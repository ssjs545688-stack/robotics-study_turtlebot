# =========================================================
# ROS2 Humble + Gazebo + MuJoCo 통합 개발용 Dockerfile
#
# 기준 이미지:
#   osrf/ros:humble-desktop
#
# 목적:
#   - ROS2 Humble
#   - C++ / Python 개발환경
#   - Gazebo 시뮬레이션
#   - TurtleBot3 시뮬레이션
#   - Nav2
#   - MuJoCo
#   - OpenCV
#   - Stable-Baselines3 강화학습
#   - YOLO
#   - X11 GUI 출력
# =========================================================

FROM osrf/ros:humble-desktop

# ---------------------------------------------------------
# 1. 기본 쉘 설정
# ---------------------------------------------------------

SHELL ["/bin/bash", "-c"]

# ---------------------------------------------------------
# 2. 환경 변수 설정
# ---------------------------------------------------------

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# MuJoCo OpenGL
ENV MUJOCO_GL=glfw

# Python 출력 버퍼 비활성화
ENV PYTHONUNBUFFERED=1

# ---------------------------------------------------------
# 3. 기본 개발 도구
# ---------------------------------------------------------

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    nano \
    vim \
    tree \
    terminator \
    net-tools \
    iputils-ping \
    wget \
    curl \
    unzip \
    terminator \
    pkg-config \
    python3-pip \
    python3-dev \
    python3-venv \
    python3-colcon-common-extensions \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 4. Gazebo 설치
# ---------------------------------------------------------

RUN apt-get update && apt-get install -y \
    gazebo \
    libgazebo-dev \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-gazebo-plugins \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 5. TurtleBot3 시뮬레이션
# ---------------------------------------------------------

RUN apt-get update && apt-get install -y \
    ros-humble-turtlebot3 \
    ros-humble-turtlebot3-simulations \
    ros-humble-turtlebot3-gazebo \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 6. Nav2
# ---------------------------------------------------------

RUN apt-get update && apt-get install -y \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 7. ROS2 추가 패키지
# ---------------------------------------------------------

RUN apt-get update && apt-get install -y \
    ros-humble-tf2 \
    ros-humble-tf2-ros \
    ros-humble-tf2-tools \
    ros-humble-rviz2 \
    ros-humble-image-transport \
    ros-humble-cv-bridge \
    ros-humble-sensor-msgs \
    ros-humble-geometry-msgs \
    ros-humble-nav-msgs \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 8. OpenCV
# ---------------------------------------------------------

RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 9. Python 가상환경 생성
#
# ROS2의 시스템 Python 환경과
# MuJoCo / RL / YOLO 환경을 분리
# ---------------------------------------------------------

RUN python3 -m venv --system-site-packages /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

# ---------------------------------------------------------
# 10. pip / setuptools 버전 설정
#
# ROS2 colcon-core와 충돌하지 않도록
# setuptools 80 미만으로 제한
# ---------------------------------------------------------

RUN pip install --no-cache-dir \
    "setuptools>=30.3.0,<80"

# ---------------------------------------------------------
# 11. MuJoCo / 강화학습 환경
# ---------------------------------------------------------

RUN pip install --no-cache-dir \
    mujoco \
    gymnasium \
    stable-baselines3 \
    numpy \
    scipy \
    matplotlib \
    imageio \
    imageio-ffmpeg

# ---------------------------------------------------------
# 12. YOLO / Computer Vision
# ---------------------------------------------------------

RUN pip install --no-cache-dir \
    ultralytics

# ---------------------------------------------------------
# 13. rosdep 초기화
# ---------------------------------------------------------

RUN rosdep init || true
RUN rosdep update || true

# ---------------------------------------------------------
# 14. TurtleBot3 기본 모델
# ---------------------------------------------------------

ENV TURTLEBOT3_MODEL=burger

# ---------------------------------------------------------
# 15. 작업공간 생성
# ---------------------------------------------------------

WORKDIR /root/ros2_ws

RUN mkdir -p \
    /root/ros2_ws/src \
    /root/mujoco_ws \
    /root/project

# ---------------------------------------------------------
# 16. ROS2 환경 자동 로드
# ---------------------------------------------------------

RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

RUN echo "export TURTLEBOT3_MODEL=burger" >> /root/.bashrc

RUN echo "if [ -f /root/ros2_ws/install/setup.bash ]; then source /root/ros2_ws/install/setup.bash; fi" >> /root/.bashrc

# ---------------------------------------------------------
# 17. Gazebo 환경변수
# ---------------------------------------------------------

RUN echo 'export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/opt/ros/humble/share/turtlebot3_gazebo/models' >> /root/.bashrc

# ---------------------------------------------------------
# 18. MuJoCo 환경변수
# ---------------------------------------------------------

RUN echo 'export MUJOCO_GL=glfw' >> /root/.bashrc

# ---------------------------------------------------------
# 19. 기본 실행
# ---------------------------------------------------------

CMD ["/bin/bash"]