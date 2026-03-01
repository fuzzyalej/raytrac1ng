// 05-two-lights.pov — two area lights, three spheres with varying size,
// color, and transparency. Shadows from both lights overlap to create
// complex lit/penumbra/umbra regions.
camera {
  location <0, 4, -8>
  look_at <0, 0.8, 0>
  fov 55
}

// Warm key light from upper-left
light {
  position <-5, 7, -3>
  radius 1.2
  samples 32
}

// Cool fill light from upper-right — softer, further away
light {
  position <6, 5, -2>
  radius 2.0
  samples 32
}

// Ground plane
plane {
  normal <0, 1, 0>
  offset 0
  color gray
}

// Large opaque orange sphere — casts the biggest shadow
sphere {
  center <-1.5, 1.2, 1.5>
  radius 1.2
  color orange
}

// Medium semi-transparent cyan sphere — tints the shadow beneath it
sphere {
  center <1.2, 0.8, 0.2>
  radius 0.8
  color cyan
  opacity 0.45
}

// Small nearly-transparent magenta sphere — barely visible, faint shadow
sphere {
  center <0, 0.35, -1.8>
  radius 0.35
  color magenta
  opacity 0.15
}
