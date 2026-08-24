cmake_minimum_required(VERSION 3.8)
project(turtle_vision)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)

# add_executable(...)
# ament_target_dependencies(...)

# [M-3 수정] RENAME 추가: ros2 run turtle_vision yolo_node 으로 실행 가능하게
install(PROGRAMS src/yolo_node.py DESTINATION lib/${PROJECT_NAME} RENAME yolo_node)

install(DIRECTORY
  launch
  config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
