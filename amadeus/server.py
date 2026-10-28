"""Local workbench: frozen specialist models and project-based research tools."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import html
import io
import json
import mimetypes
import os
import sys
from pathlib import Path
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from . import workflow
import uuid

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'amadeus/web'
ASSETS = ROOT / 'amadeus/assets'
RUNS = ROOT / 'outputs/amadeus'
ARCHIVE = json.loads((WEB / 'replay.json').read_text())
POOLS = {p['id']: p for p in ARCHIVE['pools']}
MODELS = json.loads((ASSETS / 'models.json').read_text())
JOBS = {}
LOCK = threading.Lock()
COMPUTE = threading.Lock()


def model_path(pool):
    # Only bundled trusted models or an explicitly configured local model directory.
    custom = os.environ.get('AMADEUS_MODEL_DIR')
    if custom:
        path = Path(custom) / f'{pool}.joblib'
        if path.is_file():
            return path
    if pool in MODELS:
        return ASSETS / MODELS[pool]['file']
    return None


def public_molecule(index):
    return {k: v for k, v in ARCHIVE['molecules'][index].items() if not k.startswith('gold_')}


def display_name(molecule):
    return f"配体 {molecule['label']}" if molecule['name'] == molecule['smiles'] else molecule['name']


def catalog():
    return {'version': '1.0', 'case': 'CsPbBr3 纳米晶发光优化',
            'molecules': [public_molecule(i) for i in range(len(ARCHIVE['molecules']))],
            'pools': [{'id': p['id'], 'train_count': len(p['train']), 'test_count': len(p['test']),
                       'live': model_path(p['id']) is not None, 'test': p['test']} for p in POOLS.values()],
            'default_pool': ARCHIVE['default_pool'], 'default_budget': 3,
            'source': '公开实测档案 · 90种配体 × 40个用量点', 'local': True}


def save_job(job):
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / f"{job['id']}.json").write_text(json.dumps(job, ensure_ascii=False, allow_nan=False, indent=2))


def update(job, stage, message):
    with LOCK:
        job['stage'] = stage
        job['message'] = message
        job['events'].append({'stage': stage, 'message': message, 'at': round(time.time(), 3)})


def execute(job):
    start = time.monotonic()
    try:
        p = POOLS[job['pool']]
        update(job, 0, '已确认候选与训练身份隔离，检查用量及特征输入。')
        if job['mode'] == 'live':
            import joblib
            import numpy as np
            from allis_delivery.core import Dataset, predict_models, environment
            path = model_path(job['pool'])
            if path is None:
                raise ValueError('这一候选组未安装模型权重，请选择候选组01或历史回放。')
            if path.parent == ASSETS:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest != MODELS[job['pool']]['sha256']:
                    raise ValueError('模型文件校验失败，请恢复仓库中的模型文件。')
            with COMPUTE:
                environment()
                data = Dataset()
                candidate = data.candidates(data.split(job['pool']))
                bundle = joblib.load(path)
                if bundle.split != job['pool'] or bundle.training_ids != [data.ids[i] for i in p['train']]:
                    raise ValueError('模型与候选组身份不匹配。')
                update(job, 1, '正在加载已训练的双模型，对18个候选执行预测。')
                prediction = predict_models(bundle, candidate)
                # This is a lightweight wiring check, not a new performance experiment.
                job['reference_max_abs_error'] = max(float(np.max(np.abs(np.asarray(prediction[k]) - np.asarray(p[k]))))
                                                    for k in ('paired_q', 'direct_q', 'paired_curves'))
                job['model_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            update(job, 1, '读取已核验的预测曲线和直接评分，重新计算融合排名。')
            prediction = {k: copy.deepcopy(p[k]) for k in ('ids', 'paired_q', 'direct_q', 'paired_curves', 'dose_pmol')}
        from allis_delivery.evaluation import ranks, replay_selection
        update(job, 2, '两路评分已生成，以固定50% / 50%规则融合名次。')
        rank = {k: v.tolist() for k, v in ranks(prediction['paired_q'], prediction['direct_q']).items()}
        rank.update({k: p['ranks'][k] for k in ('random', 'paired_RF', 'paired_RF_CI')})
        orders = {k: replay_selection(v, len(v), seed=42).tolist() for k, v in rank.items()}
        result = {'id': p['id'], 'test': p['test'], 'train': p['train'], **prediction,
                  'rf_curves': p['rf_curves'], 'ranks': rank, 'orders': orders,
                  'selected': orders['equal_rank'][:job['budget']]}
        with LOCK:
            job['result'] = result
            job['status'] = 'complete'
            job['seconds'] = round(time.monotonic() - start, 3)
        update(job, 3, '推荐名单已生成。实测结果仍未发送至推荐页面。')
        save_job(job)
    except Exception as exc:
        with LOCK:
            job.update(status='failed', message=f'运行未完成：{exc}', seconds=round(time.monotonic() - start, 3))
        save_job(job)


def reveal(job):
    import numpy as np
    from allis_delivery.evaluation import expected_best
    result = job['result']
    gold = [ARCHIVE['molecules'][i]['gold_Q'] for i in result['test']]
    metrics = {}
    for method, rank in result['ranks'].items():
        curve = expected_best(rank, gold)
        metrics[method] = {'curve': curve.tolist(), 'AUR': float(np.mean(max(gold) - curve)),
                           'oracle_Q': max(gold),
                           'selected_best': max(gold[i] for i in result['orders'][method][:job['budget']])}
    return {'molecules': [{k: v for k, v in ARCHIVE['molecules'][i].items() if k in ('index', 'gold_Q', 'gold_curve')}
                          for i in result['test']], 'metrics': metrics,
            'summary': ARCHIVE['summary'], 'comparisons': ARCHIVE['comparisons']}


def rows(job):
    p = job['result']
    return [{'priority': k + 1, 'label': ARCHIVE['molecules'][p['test'][i]]['label'],
             'name': display_name(ARCHIVE['molecules'][p['test'][i]]),
             'paired_Q': p['paired_q'][i], 'direct_Q': p['direct_q'][i],
             'paired_rank': p['ranks']['paired_ET'][i], 'direct_rank': p['ranks']['direct_Q_ET'][i],
             'fusion_rank_value': p['ranks']['equal_rank'][i]}
            for k, i in enumerate(p['selected'])]


def csv_report(job):
    stream = io.StringIO()
    data = rows(job)
    writer = csv.DictWriter(stream, fieldnames=list(data[0]))
    writer.writeheader()
    for row in data:
        # Spreadsheet-safe text, even if a future supplied name starts with a formula prefix.
        writer.writerow({k: "'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v for k, v in row.items()})
    return ('\ufeff' + stream.getvalue()).encode('utf-8')


def report(job, include_measured=False):
    esc = html.escape
    result = job['result']
    body = ''.join('<tr>' + ''.join(f'<td>{esc(str(round(v, 4) if isinstance(v, float) else v))}</td>' for v in row.values()) + '</tr>' for row in rows(job))
    cards = ''
    for i in result['selected']:
        m = ARCHIVE['molecules'][result['test'][i]]
        values = result['paired_curves'][i]
        low, high = min(0, min(values)), max(values) * 1.08
        doses = result['dose_pmol'][i]
        points = ' '.join(f'{20+480*(dose-doses[0])/(doses[-1]-doses[0]):.2f},{135-110*(y-low)/(high-low or 1):.2f}' for dose, y in zip(doses, values))
        cards += f'<section><h2>{esc(display_name(m))}</h2><div class="structure">{m["svg"]}</div><svg viewBox="0 0 520 160" role="img" aria-label="预测用量响应曲线"><path d="M20 20V135H500" fill="none" stroke="#bbc4bf"/><polyline points="{points}" fill="none" stroke="#315f91" stroke-width="2.5"/></svg><p>成对模型预测；用量 {doses[0]/1000:.2f}—{doses[-1]/1000:.2f} nmol，相对发光 FOM {min(values):.3f}—{max(values):.3f}。</p></section>'
    mode = '已保存模型的本机推断' if job['mode'] == 'live' else '历史预测的排名复算'
    measured = ''
    if include_measured:
        evidence = reveal(job)
        q = evidence['metrics']['equal_rank']
        measured = f'<section><h2>已揭晓的历史实测对照</h2><p>本轮推荐名单中的最好实测Q为 {q["selected_best"]:.4f}，当前候选池最佳实测Q为 {q["oracle_Q"]:.4f}。这是公开数据的回顾性验证。</p><table><thead><tr><th>策略</th><th>本轮名单最好Q</th><th>同分随机期望Q</th></tr></thead><tbody>'
        for method, label in [('random', '随机选择'), ('paired_RF', '成对RF'), ('paired_ET', '成对ET'), ('direct_Q_ET', '直接评分ET'), ('equal_rank', '等权融合')]:
            item = evidence['metrics'][method]
            measured += f'<tr><td>{label}</td><td>{item["selected_best"]:.4f}</td><td>{item["curve"][job["budget"]-1]:.4f}</td></tr>'
        measured += '</tbody></table></section>'
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Amadeus · 实验决策报告</title>
<style>body{{font:15px/1.7 system-ui,sans-serif;color:#243a34;max-width:1050px;margin:50px auto;padding:0 25px}}h1{{font-size:32px}}h2{{font-size:19px}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{padding:10px 8px;border-bottom:1px solid #ddd;text-align:left}}section{{break-inside:avoid;border-top:1px solid #ddd;padding-top:18px;margin-top:30px}}section>svg{{max-width:480px;vertical-align:middle}}.structure{{display:inline-block;width:230px;vertical-align:middle}}.structure svg{{width:100%;height:150px}}small,p{{color:#53645c}}@media print{{body{{margin:0}}button{{display:none}}}}</style>
<button onclick="window.print()">打印 / 保存为 PDF</button><h1>Amadeus · 实验决策报告</h1>
<p>任务：CsPbBr₃纳米晶配体筛选 · 目标：提高推荐集中的最佳发光表现</p>
<p>候选组 {esc(job['pool'])} · 36个历史配体 / 18个候选 · 本轮推荐 {job['budget']} 个<br>运行方式：{mode} · 耗时 {job['seconds']} 秒<br>记录：{esc(job['id'])} · {esc(job['created_at'])}</p>
<table><thead><tr>{''.join(f'<th>{v}</th>' for v in ['优先级','标识','候选','曲线预测Q','直接预测Q','曲线名次','直接名次','融合名次值'])}</tr></thead><tbody>{body}</tbody></table>
<p>两路名次各占50%；并列使用固定seed 42。Q为40个用量点最高4个相对发光FOM的均值。建议依据是模型预测与排序，不是已证明的化学机理。实测答案不参与推荐。</p>
{measured}{cards}<section><h2>方法与数据记录</h2><p>公开实测档案，90种完整配体曲线。当前模型使用原42维描述符和2048维Morgan计数指纹。无本次训练或调参。结果用于回顾性筛选与下一步测试讨论；实验用量及可行性仍需研究者核对。</p><p>模型摘要：{esc(job.get('model_sha256', '历史预测复算'))}</p><p>来源：Kim et al., ACS Nano 2024, DOI 10.1021/acsnano.4c02094；完整资源归属见仓库THIRD_PARTY.md。</p></section></html>'''.encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    def send(self, data, status=200, content_type='application/json; charset=utf-8', filename=None):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == '/api/config':
                return self.send({'local': True, 'provider': 'DeepSeek', 'configured': bool(workflow.provider.settings().get('DEEPSEEK_API_KEY'))})
            if path == '/api/projects':
                return self.send(workflow.listing())
            if path.startswith('/api/projects/'):
                parts = path.strip('/').split('/')
                project = workflow.load(parts[2])
                if len(parts) == 3:
                    return self.send(workflow.visible(project))
                if parts[3] == 'report':
                    return self.send(workflow.export_report(project), content_type='text/html; charset=utf-8')
                if parts[3] == 'csv':
                    return self.send(workflow.export_csv(project), content_type='text/csv; charset=utf-8', filename='amadeus-plan.csv')
                if parts[3] == 'export':
                    return self.send(project, filename='amadeus-project.json')
            if path == '/api/catalog':
                return self.send(catalog())
            if path == '/api/history':
                return self.send([{'id': j['id'], 'pool': j['pool'], 'budget': j['budget'], 'mode': j['mode'],
                                   'status': j['status'], 'created_at': j['created_at']} for j in list(JOBS.values())[-20:][::-1]])
            if path.startswith('/api/jobs/'):
                parts = path.strip('/').split('/')
                with LOCK:
                    job = copy.deepcopy(JOBS.get(parts[2]))
                if not job:
                    return self.send({'error': '运行记录不存在。'}, 404)
                if len(parts) == 3:
                    return self.send(job)
                if job['status'] != 'complete':
                    return self.send({'error': '请等待计算完成。'}, 409)
                if parts[3] == 'reveal':
                    return self.send(reveal(job))
                if parts[3] == 'report':
                    measured = parse_qs(urlparse(self.path).query).get('measured') == ['1']
                    return self.send(report(job, measured), content_type='text/html; charset=utf-8')
                if parts[3] == 'csv':
                    return self.send(csv_report(job), content_type='text/csv; charset=utf-8', filename=f'amadeus-{job["id"]}.csv')
            # Explicit static allowlist: raw data, models and archived answers are not served locally.
            files = {'/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js',
                     '/style.css': 'style.css', '/mark.svg': 'mark.svg', '/classic.html':'classic.html',
                     '/demo-adapter.js':'demo-adapter.js', '/workbench.js':'workbench.js', '/workbench.css':'workbench.css', '/case-molecule.svg':'case-molecule.svg',
                     '/sample-history.csv':'sample-history.csv', '/sample-candidates.csv':'sample-candidates.csv'}
            if path in files:
                file = WEB / files[path]
                return self.send(file.read_bytes(), content_type=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
            return self.send({'error': '路径不存在。'}, 404)
        except Exception as exc:
            return self.send({'error': str(exc)}, 500)

    def do_POST(self):
        # Refuse cross-origin browser requests; this server is intentionally loopback-only.
        origin = self.headers.get('Origin')
        if origin and origin != f'http://{self.headers.get("Host")}':
            return self.send({'error': '跨来源请求已拒绝。'}, 403)
        path = urlparse(self.path).path
        if path == '/api/projects' or path.startswith('/api/projects/'):
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 8_000_000:
                    raise ValueError('请使用小于8MB的请求。')
                data = json.loads(self.rfile.read(length))
                if path == '/api/projects':
                    return self.send(workflow.visible(workflow.create(data)))
                parts = path.strip('/').split('/')
                if len(parts) == 4 and parts[3] == 'action':
                    return self.send(workflow.start(parts[2], data), 202)
                if len(parts) == 4 and parts[3] == 'cancel':
                    return self.send(workflow.cancel(parts[2]))
                return self.send({'error':'路径不存在。'},404)
            except (ValueError, KeyError, TypeError) as exc:
                return self.send({'error':str(exc)},400)
        if path != '/api/run':
            return self.send({'error': '路径不存在。'}, 404)
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 4096:
                raise ValueError('请求大小无效。')
            data = json.loads(self.rfile.read(length))
            pool, budget, mode = data.get('pool'), data.get('budget'), data.get('mode')
            if pool not in POOLS or type(budget) is not int or not 1 <= budget <= 5 or mode not in ('live', 'replay'):
                raise ValueError('请选择有效的候选组、1—5个推荐名额和运行方式。')
            if mode == 'live' and model_path(pool) is None:
                raise ValueError('此候选组仅支持历史回放，请切换候选组01执行模型推断。')
            with LOCK:
                if any(j['status'] == 'running' for j in JOBS.values()):
                    return self.send({'error': '已有任务运行中，请等待完成。'}, 409)
                job = {'id': uuid.uuid4().hex[:12], 'pool': pool, 'budget': budget, 'mode': mode,
                       'created_at': datetime.now(timezone.utc).isoformat(), 'status': 'running',
                       'stage': 0, 'events': [], 'message': '准备输入'}
                JOBS[job['id']] = job
            threading.Thread(target=execute, args=(job,), daemon=True).start()
            return self.send({'id': job['id']}, 202)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send({'error': str(exc)}, 400)

    def log_message(self, fmt, *args):
        print(f'[Amadeus] {fmt % args}', flush=True)


def main():
    parser = argparse.ArgumentParser(description='Amadeus local workbench')
    parser.add_argument('--port', type=int, default=8787)
    args = parser.parse_args()
    if RUNS.exists():
        for path in sorted(RUNS.glob('*.json'), key=lambda p: p.stat().st_mtime)[-20:]:
            try:
                job = json.loads(path.read_text())
                if job['status'] in ('complete', 'failed'):
                    JOBS[job['id']] = job
            except (ValueError, KeyError):
                continue
    workflow.init(sys.modules[__name__])
    print(f'Amadeus is ready: http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
