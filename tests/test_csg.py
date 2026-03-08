"""Tests for CSG — data structures, interval operations, and shape classes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shapes import HitInterval, HitRecord
from vector import Vec3


def test_hit_interval_fields():
    n = Vec3(1, 0, 0)
    iv = HitInterval(1.0, 3.0, n, Vec3(-1, 0, 0), None, None)
    assert iv.t_enter == 1.0
    assert iv.t_exit == 3.0
    assert iv.enter_normal == n


def test_hit_record_mat_obj_default():
    rec = HitRecord(t=1.0, point=Vec3(0,0,0), normal=Vec3(0,1,0))
    assert rec.mat_obj is None
