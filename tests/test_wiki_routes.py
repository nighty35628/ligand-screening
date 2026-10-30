"""Documentation routes must not expose workspace files or require model execution."""
import json
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from amadeus.server import Handler

class WikiRoutes(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.base=f'http://127.0.0.1:{cls.server.server_port}'
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
 def test_documentation_and_assets(self):
  for path,mime in [('/wiki/','text/html'),('/wiki/models/','text/html'),('/wiki/wiki.css','text/css'),('/wiki/search-index.json','application/json'),('/sitemap.xml','application/xml')]:
   with self.subTest(path=path),urllib.request.urlopen(self.base+path) as response:
    self.assertEqual(response.status,200);self.assertIn(mime,response.headers['Content-Type']);self.assertGreater(len(response.read()),100)
 def test_directory_redirect(self):
  for path in ['/wiki','/wiki/models']:
   with urllib.request.urlopen(self.base+path) as response:self.assertTrue(response.url.endswith('/'))
 def test_non_public_paths_are_rejected(self):
  for path in ['/wiki/missing/','/wiki/%2e%2e/.env.local','/wiki/../logo.svg','/wiki/%2e%2e/%2e%2e/outputs/','/wiki/%5c..%5c.env.local']:
   with self.subTest(path=path),self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.base+path)
   self.assertEqual(error.exception.code,404)
if __name__=='__main__':unittest.main()
