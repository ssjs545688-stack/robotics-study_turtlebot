cmake_minimum_required(VERSION 3.8)
project(turtle_fms)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)

# add_executable(...)
# ament_target_dependencies(...)

install(PROGRAMS src/fms_node.py DESTINATION lib/${PROJECT_NAME} RENAME fms_node)

install(DIRECTORY
  launch
  config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
