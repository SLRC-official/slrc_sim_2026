cmake_minimum_required(VERSION 3.8)
project(slrc_tron_sim)

find_package(ament_cmake REQUIRED)

# Install non-compiled resources
install(DIRECTORY
  launch
  worlds
  urdf
  meshes
  config
  scripts
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
