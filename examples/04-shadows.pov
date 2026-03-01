// 04-shadows.pov — showcase of soft shadows from a sphere area light
camera {
  location <0, 3, -7>
  look_at <0, 0.5, 0>
  fov 55
}

// Area light: radius > 0 fires multiple shadow rays for soft penumbra
light {
  position <4, 6, -4>
  radius 1.5
  samples 32
}

// Ground plane
plane {
  normal <0, 1, 0>
  offset 0
  color gray
}

// Large white sphere casting a wide shadow
sphere {
  center <-1.2, 1, 1>
  radius 1.0
  color white
}

// Small red sphere with a tight shadow
sphere {
  center <1.5, 0.4, 0>
  radius 0.4
  color red
}

// Semi-transparent blue sphere — partially blocks light
sphere {
  center <0, 0.6, -1>
  radius 0.6
  color blue
  opacity 0.5
}
