import unittest
import os
import sys

# Add src to path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.parsers.pow_parser import parse_source, SceneMesh, SceneTransform

class TestMeshTransform(unittest.TestCase):
    def test_mesh_parsing_with_transform(self):
        src = """
        let xf = transform { scale (2, 2, 2) }
        mesh {
            file "dummy.obj"
            transform xf
        }
        """
        items = parse_source(src)
        mesh_item = next(item for item in items if isinstance(item, SceneMesh))
        self.assertIsNotNone(mesh_item.transform)
        self.assertIsInstance(mesh_item.transform, SceneTransform)
        self.assertEqual(mesh_item.transform.scale, (2, 2, 2))

if __name__ == "__main__":
    unittest.main()
