// 03-transparency.pov — showcase of alpha blending transparency
camera {
  location <0, 2.5, -6>
  look_at <0, 0.5, 0>
  fov 60
}

light {
  position <5, 10, -3>
}

// Ground plane
plane {
  normal <0, 1, 0>
  offset 0
  color gray
}

// Solid blue sphere at the back
sphere {
  center <0, 1, 2>
  radius 1.0
  color blue
}

// Semi-transparent red sphere in the middle
sphere {
  center <0, 1, 0>
  radius 1.0
  color red
  opacity 0.5
}

// More transparent green sphere at the front
sphere {
  center <0, 1, -2>
  radius 1.0
  color green
  opacity 0.25
}
