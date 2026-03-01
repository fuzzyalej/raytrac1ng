"""Unit tests for _refract() and _schlick() math helpers."""
import math
from vector import Vec3
from renderer import _refract, _schlick


def test_straight_through_same_medium():
    """n1 == n2: ray passes straight through, direction unchanged."""
    D = Vec3(0, -1, 0)
    N = Vec3(0, 1, 0)
    result = _refract(D, N, 1.0, 1.0)
    assert result is not None
    assert abs(result.x) < 1e-9
    assert abs(result.y - (-1.0)) < 1e-9
    assert abs(result.z) < 1e-9


def test_bends_toward_normal_entering_denser():
    """Ray at 45° entering glass (n=1.5) bends toward normal."""
    D = Vec3(1, -1, 0).normalize()   # 45° angle of incidence
    N = Vec3(0, 1, 0)
    result = _refract(D, N, 1.0, 1.5)
    assert result is not None
    # Snell: sin(theta_t) = (1.0/1.5) * sin(45°)
    expected_sin_t = (1.0 / 1.5) * math.sin(math.radians(45))
    actual_sin_t = abs(result.x)   # x-component = sin(theta_t) for this geometry
    assert abs(actual_sin_t - expected_sin_t) < 1e-6


def test_bends_away_from_normal_exiting():
    """Ray exiting denser medium bends away from normal."""
    # Small angle (30°) from normal, well below critical angle
    angle = math.radians(30)
    D = Vec3(math.sin(angle), -math.cos(angle), 0)
    N = Vec3(0, 1, 0)
    result = _refract(D, N, 1.5, 1.0)
    assert result is not None
    # Transmitted angle > incident angle (bends away from normal)
    assert abs(result.x) > abs(D.x)


def test_total_internal_reflection():
    """Angle beyond critical angle returns None (TIR)."""
    # Critical angle for n1=1.5, n2=1.0: arcsin(1/1.5) ≈ 41.8°
    # Use 50°: beyond critical angle → TIR
    angle = math.radians(50)
    D = Vec3(math.sin(angle), -math.cos(angle), 0)
    N = Vec3(0, 1, 0)
    result = _refract(D, N, 1.5, 1.0)
    assert result is None


def test_just_below_critical_angle_passes():
    """Angle just below critical angle does NOT produce TIR."""
    # Critical angle ≈ 41.8°; use 40°
    angle = math.radians(40)
    D = Vec3(math.sin(angle), -math.cos(angle), 0)
    N = Vec3(0, 1, 0)
    result = _refract(D, N, 1.5, 1.0)
    assert result is not None


def test_schlick_equals_r0_at_normal_incidence():
    """At cos_theta=1 (normal incidence), Schlick == R0."""
    r0 = ((1.0 - 1.5) / (1.0 + 1.5)) ** 2
    assert abs(_schlick(1.0, 1.0, 1.5) - r0) < 1e-9


def test_schlick_approaches_one_at_grazing():
    """At grazing angle (cos≈0), Schlick approaches 1.0."""
    r = _schlick(0.001, 1.0, 1.5)
    assert r > 0.99


def test_schlick_between_zero_and_one():
    """Schlick always returns a value in [0, 1]."""
    for cos_theta in [0.0, 0.25, 0.5, 0.75, 1.0]:
        r = _schlick(cos_theta, 1.0, 1.5)
        assert 0.0 <= r <= 1.0


def test_schlick_clamps_negative_cos_theta():
    """Negative cos_theta is clamped; result stays in [0, 1]."""
    r = _schlick(-0.1, 1.0, 1.5)
    assert 0.0 <= r <= 1.0
