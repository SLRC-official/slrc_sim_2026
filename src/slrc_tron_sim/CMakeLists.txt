cmake_minimum_required(VERSION 3.8)
project(slrc_tron_sim)

find_package(ament_cmake REQUIRED)

# Install non-compiled resources
install(DIRECTORY
  worlds
  urdf
  meshes
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
