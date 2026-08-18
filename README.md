# 🤖 ADAS Telos: 하이브리드 다중 로봇 물류 시뮬레이션 프로젝트

**ADAS Telos**는 대규모 환경 모사에 최적화된 **Gazebo**와 정밀한 접촉 동역학 및 물리 연산에 특화된 **MuJoCo**를 통합한 하이브리드 시뮬레이션 환경입니다. 
본 프로젝트는 실제 물류 창고와 유사한 대규모 가상 환경에서 4대의 **TurtleBot3 Waffle Pi**가 자율 주행(Nav2) 및 화물 이송 임무를 수행하는 다중 로봇 관제 시스템(FMS)을 검증하는 것을 목표로 합니다.

---

## 🏗 시스템 아키텍처 및 기술 스택

* **시뮬레이션 엔진:** `Gazebo` (대규모 맵, 센서 레이캐스팅) + `MuJoCo` (타이어 마찰, 서스펜션, 화물 적재 충격 연산)
* **로봇 하드웨어:** `TurtleBot3 Waffle Pi` 4대 (LDS-01/02 LiDAR 및 RGB-D 카메라 탑재)
* **운영체제 및 프레임워크:** `ROS 2 Humble` (Docker 환경)
* **자율주행 및 관제:** `Navigation2 (Nav2)`, 커스텀 `FMS (Fleet Management System)`
* **인공지능 (비전):** `YOLO (v8)` 기반 동적 장애물(작업자) 및 화물 인식

---

## 📁 주요 ROS 2 패키지 구조

전체 프로젝트는 `workspace/src` 내에 7개의 핵심 패키지로 모듈화되어 있습니다.

| 패키지명 | 주요 역할 | 상태 |
| --- | --- | --- |
| `telos_gazebo` | 20x20m 물류 창고 맵(`warehouse.world`) 및 4대의 다중 터틀봇 Spawn 런치 구성 | 완료 (Skeleton) |
| `telos_mujoco` | 3kg 화물(`box_3kg.xml`) 및 터틀봇 물리(서스펜션/적재함) 특성 모델 | 완료 (Skeleton) |
| `telos_bridge` | Gazebo와 MuJoCo 간 100Hz Lock-step 위치 및 힘/토크 동기화 C++ 노드 | 완료 (Skeleton) |
| `telos_navigation` | 각 로봇의 독립된 네임스페이스를 가지는 다중 로봇 Nav2 실행 런치 구성 | 완료 (Skeleton) |
| `telos_vision` | `/camera/image_raw`를 구독하여 화물/작업자를 검출하는 YOLO Python 노드 | 완료 (Skeleton) |
| `telos_fms` | 배터리 상태 기반 최적 로봇 3대 할당 및 교차로 양보 트래픽 제어 노드 | 완료 (Skeleton) |
| `telos_scenario` | 지속가능한 화물 순환(Spawn/Despawn) 및 전력 소모 모델 관리 노드 | 완료 (Skeleton) |

---

## 🚀 빠른 시작 (Quick Start)

### 1. 환경 설정 및 빌드
본 프로젝트는 Docker 환경(`docker-compose.yml`)을 기반으로 동작합니다.

```bash
# 1. 도커 컨테이너 백그라운드 실행
docker-compose up -d

# 2. 도커 컨테이너 내부로 진입
docker exec -it robotics-sim /bin/bash

# 3. ROS 2 패키지 빌드
cd /root/ros2_ws
colcon build
source install/setup.bash
```

### 2. 시뮬레이터 실행
```bash
# 물류 창고 맵 띄우기 (Gazebo)
ros2 launch telos_gazebo warehouse.launch.py

# 새로운 터미널에서 터틀봇 4대 스폰(Spawn)하기
ros2 launch telos_gazebo spawn_turtlebots.launch.py
```
*(주의: Gazebo UI를 띄우기 위해서는 Windows 호스트에 VcXsrv, Xming 등의 X Server 프로그램이 구동 중이어야 합니다.)*

---

## 📌 주요 시나리오 흐름

1. **작업 할당 (Task Allocation):** FMS가 4대의 터틀봇 중 배터리 및 현재 상태를 고려하여 3대를 선별 후 작업 하달.
2. **트래픽 제어 (Traffic Control):** Nav2 및 FMS 양보 로직을 통해 좁은 교차로에서 병목 현상 및 충돌(Deadlock) 방지.
3. **물리 기반 상호작용 (Physics):** MuJoCo 엔진을 통해 3kg 화물이 적재될 때의 충격량, 서스펜션 변화가 차체 주행 관성에 미치는 영향을 계산.
4. **동적 장애물 회피:** 이동하는 작업자 모델 출현 시 YOLO 비전 노드가 이를 인식하고 Nav2 Replanning을 통해 관성을 유지하며 우회.

---

## 📝 라이선스
Apache License 2.0
