# 🔍 워크스페이스 전체 코드 점검 보고서

> 점검 일시: 2026-08-19  
> 대상 패키지: `turtle_bridge`, `turtle_fms`, `turtle_gazebo`, `turtle_mujoco`, `turtle_navigation`, `turtle_scenario`, `turtle_vision`

---

## 요약 (심각도 분류)

| 심각도 | 건수 | 내용 |
|--------|------|------|
| 🔴 CRITICAL | 4 | 런타임 시 즉시 크래시/동작 불가 |
| 🟠 HIGH | 6 | 기능 오작동, 데이터 오류 가능성 높음 |
| 🟡 MEDIUM | 5 | 잠재적 오류, 누락된 의존성 |
| 🔵 LOW | 4 | 코드 품질, 개선 권장 |

---

## 🔴 CRITICAL 오류

### [C-1] `spawn_turtlebots.launch.py` — 런치 시점에 파일 I/O 발생 (크래시 위험)
**파일**: [spawn_turtlebots.launch.py](file:///c:/work/turtlebot/workspace/src/turtle_gazebo/launch/spawn_turtlebots.launch.py#L51-L52)

```python
# 문제: generate_launch_description()은 런치 시스템 초기화 단계에서 실행
# 파일이 없으면 즉시 FileNotFoundError → 런치 전체 종료
with open(urdf_file_path, 'r') as infp:
    robot_desc = infp.read()
```

**원인**: `turtlebot3_description` 패키지가 설치되지 않았거나, `TURTLEBOT3_MODEL` 환경변수가 미설정된 경우, `urdf_file_path` 자체가 존재하지 않아 `FileNotFoundError`로 런치 전체가 즉시 실패합니다. 특히 **루프 내에서 반복**되므로 4번 시도합니다.

**해결방법**:
```python
# 환경변수 미설정 방어 + 파일 존재 확인
TURTLEBOT3_MODEL = os.environ.get('TURTLEBOT3_MODEL', 'waffle_pi')  # 기본값 제공
# urdf open 전에 존재 여부 확인
if not os.path.exists(urdf_file_path):
    raise FileNotFoundError(f'URDF not found: {urdf_file_path}')
```

---

### [C-2] `spawn_turtlebots.launch.py` — `TURTLEBOT3_MODEL` 환경변수 KeyError
**파일**: [spawn_turtlebots.launch.py](file:///c:/work/turtlebot/workspace/src/turtle_gazebo/launch/spawn_turtlebots.launch.py#L11)

```python
# 문제: 환경변수 없으면 KeyError로 즉시 종료
TURTLEBOT3_MODEL = os.environ['TURTLEBOT3_MODEL']
```

`os.environ['KEY']` 방식은 해당 환경변수가 없을 때 `KeyError`를 발생시킵니다. 시스템에서 이 환경변수를 별도로 export하지 않으면 런치 자체가 불가합니다.

**해결방법**:
```python
TURTLEBOT3_MODEL = os.environ.get('TURTLEBOT3_MODEL', 'waffle_pi')
```

---

### [C-3] `fms_node.py` — Action Callback 내 `time.sleep()` 사용 (데드락 위험)
**파일**: [fms_node.py](file:///c:/work/turtlebot/workspace/src/turtle_fms/src/fms_node.py#L142)

```python
def get_result_cb(self, future, robot_id, target_zone):
    ...
    if status == 4: # SUCCEEDED
        # ⛔ 치명적: ROS2 executor 스레드를 블로킹
        time.sleep(2.0)
```

`MultiThreadedExecutor`를 사용하더라도, Action 콜백 내에서 `time.sleep()`을 호출하면 해당 스레드가 2초간 블로킹됩니다. 모든 로봇이 동시에 목표에 도달하면 **스레드 풀이 고갈**되어 타이머 콜백(`task_allocation_loop`)이 실행되지 않는 데드락이 발생할 수 있습니다.

**해결방법**:
```python
# time.sleep() 대신 ROS2 타이머 사용
self.create_timer(2.0, lambda: self._post_arrival_cb(robot_id), oneshot=True)
```

---

### [C-4] `rviz2.launch.py` — RViz 설정 파일 누락 (silent 실패)
**파일**: [rviz2.launch.py](file:///c:/work/turtlebot/workspace/src/turtle_navigation/launch/rviz2.launch.py#L12-L16)

```python
rviz_config = os.path.join(
    get_package_share_directory('turtle_navigation'),
    'config',
    'multi_robot_rviz.rviz'   # ← 이 파일이 존재하지 않음!
)
```

`config/` 디렉토리를 확인한 결과 `nav2_params.yaml` 외에 **`multi_robot_rviz.rviz` 파일이 없습니다**. 파일이 없으면 `os.path.exists()`가 `False`를 반환하여 RViz가 설정 없이 기본 화면으로 실행됩니다. 다중 로봇 시각화가 전혀 동작하지 않습니다.

---

## 🟠 HIGH 오류

### [H-1] `nav2_params.yaml` — 다중 로봇 프레임 불일치
**파일**: [nav2_params.yaml](file:///c:/work/turtlebot/workspace/src/turtle_navigation/config/nav2_params.yaml)

```yaml
# bt_navigator (L46)
robot_base_frame: base_link  # ← base_link 사용

# local_costmap (L128)  
robot_base_frame: base_link  # ← base_link 사용

# spawn_turtlebots.launch.py에서는 frame_prefix: 'tb1/'로 설정
# 따라서 실제 프레임 이름은 'tb1/base_link'가 됨
```

`nav2_multi.launch.py`에서 `RewrittenYaml`로 `robot_base_frame: tb1/base_footprint`로 재작성하려 시도하지만, `bt_navigator`, `local_costmap`, `global_costmap`, `behavior_server` 등은 `base_link`를 참조하고 있습니다. `amcl`만 `base_footprint`를 사용합니다. **TF 트리 불일치**로 Nav2가 동작하지 않을 가능성이 높습니다.

> [!IMPORTANT]
> TurtleBot3 Waffle Pi는 `base_footprint` → `base_link` TF를 게시합니다. 모든 파라미터를 `base_footprint`로 통일하거나 올바른 프레임 체계를 확립해야 합니다.

---

### [H-2] `nav2_params.yaml` — costmap scan 토픽이 절대경로
**파일**: [nav2_params.yaml](file:///c:/work/turtlebot/workspace/src/turtle_navigation/config/nav2_params.yaml#L151)

```yaml
local_costmap:
  scan:
    topic: /scan   # ← 절대경로! 네임스페이스 미적용
    
global_costmap:
  scan:
    topic: /scan   # ← 절대경로! 네임스페이스 미적용
```

다중 로봇 환경에서 각 로봇의 LiDAR 토픽은 `/tb1/scan`, `/tb2/scan` 등으로 게시됩니다. `/scan`(절대경로)으로 설정하면 **모든 로봇이 동일한 LiDAR 데이터를 구독**하여 충돌 회피가 완전히 실패합니다.

**해결방법**: `scan` → `scan` (상대경로, `/` 제거)

---

### [H-3] `fms_node.py` — Nav2 결과 상태 코드 하드코딩
**파일**: [fms_node.py](file:///c:/work/turtlebot/workspace/src/turtle_fms/src/fms_node.py#L136)

```python
if status == 4: # SUCCEEDED
```

Nav2의 `GoalStatus` 코드는 ROS2 버전에 따라 다를 수 있습니다. 하드코딩된 `4` 대신 표준 상수를 사용해야 합니다.

**해결방법**:
```python
from action_msgs.msg import GoalStatus
if status == GoalStatus.STATUS_SUCCEEDED:
```

---

### [H-4] `fms_node.py` — Odom 기준 목표 좌표 계산 오류 가능성
**파일**: [fms_node.py](file:///c:/work/turtlebot/workspace/src/turtle_fms/src/fms_node.py#L57)

```python
pose.header.frame_id = f'{robot_id}/odom'
# 월드 좌표 - 스폰 위치 = odom 기준 상대 좌표
pose.pose.position.x = coords['x'] - start_pose['x']
```

`odom` 프레임은 로봇 구동 시작 후 odometry 누적 오류가 발생합니다. 더 심각한 문제는 **Nav2는 일반적으로 `map` 프레임 기준의 목표를 기대**합니다. AMCL이 `map` → `odom` TF를 게시하는 구조에서 `odom` 프레임으로 목표를 전송하면 의도하지 않은 동작이 발생합니다.

---

### [H-5] `turtle_bridge` — 빌드 시스템에 실행 파일 미등록
**파일**: [CMakeLists.txt](file:///c:/work/turtlebot/workspace/src/turtle_bridge/CMakeLists.txt#L11-L12)

```cmake
# add_executable(...)   ← 주석 처리됨!
# ament_target_dependencies(...)  ← 주석 처리됨!
```

`bridge_node.cpp`가 존재하지만 `CMakeLists.txt`에서 빌드 타겟으로 등록되지 않아 **빌드해도 실행 파일이 생성되지 않습니다**.

---

### [H-6] `turtle_mujoco` — models 디렉토리가 install에 포함 안 됨
**파일**: [CMakeLists.txt](file:///c:/work/turtlebot/workspace/src/turtle_mujoco/CMakeLists.txt#L14-L18)

```cmake
install(DIRECTORY
  launch
  config
  DESTINATION share/${PROJECT_NAME}
)
# ← models 디렉토리 누락!
```

`models/` 디렉토리에 `box_3kg.xml`, `turtlebot3_waffle_pi_physics.xml`이 존재하지만 install 대상에서 빠져있어 **빌드 후 런타임에서 해당 파일 접근이 불가**합니다.

---

## 🟡 MEDIUM 이슈

### [M-1] `turtle_navigation/package.xml` — 실제 의존성 미선언
**파일**: [package.xml](file:///c:/work/turtlebot/workspace/src/turtle_navigation/package.xml)

```xml
<!-- 현재 선언된 의존성 -->
<depend>rclcpp</depend>
<depend>std_msgs</depend>

<!-- 실제 사용되는 패키지 (누락됨) -->
<!-- nav2_bringup, nav2_common, nav2_msgs 등 -->
```

`nav2_multi.launch.py`는 `nav2_bringup`, `nav2_common`을 사용하지만 `package.xml`에 `exec_depend`로 선언되지 않았습니다. `rosdep install` 시 자동 설치가 안 됩니다.

---

### [M-2] `turtle_gazebo/package.xml` — Gazebo 관련 의존성 누락
**파일**: [package.xml](file:///c:/work/turtlebot/workspace/src/turtle_gazebo/package.xml)

`spawn_turtlebots.launch.py`는 `gazebo_ros`, `turtlebot3_gazebo`, `turtlebot3_description`, `robot_state_publisher`를 사용하지만 `package.xml`에 `exec_depend`가 없습니다.

---

### [M-3] `turtle_vision/CMakeLists.txt` — 설치 파일명 미지정 (실행 불가)
**파일**: [CMakeLists.txt](file:///c:/work/turtlebot/workspace/src/turtle_vision/CMakeLists.txt#L14)

```cmake
install(PROGRAMS src/yolo_node.py DESTINATION lib/${PROJECT_NAME})
# ← RENAME yolo_node 미지정 (fms_node는 RENAME 지정됨)
```

`fms_node.py`는 `RENAME fms_node`로 확장자 없이 설치되지만, `yolo_node.py`는 `RENAME`이 없어 `yolo_node.py`로 설치됩니다. `ros2 run`시 실행 파일명 불일치 가능성이 있습니다.

---

### [M-4] `nav2_params.yaml` — `local_costmap`에 `static_layer` 플러그인 미등록
**파일**: [nav2_params.yaml](file:///c:/work/turtlebot/workspace/src/turtle_navigation/config/nav2_params.yaml#L135)

```yaml
local_costmap:
  plugins: ["voxel_layer", "inflation_layer"]  # static_layer 없음
  ...
  static_layer:               # ← 플러그인 등록 없이 파라미터만 존재
    map_subscribe_transient_local: True
```

`static_layer` 파라미터가 선언되었지만 `plugins` 리스트에 포함되지 않아 해당 설정이 **무시**됩니다. (의도적이면 파라미터 블록 자체를 제거하는 것이 명확합니다.)

---

### [M-5] `warehouse.launch.py` — `LaunchConfiguration` import 후 미사용
**파일**: [warehouse.launch.py](file:///c:/work/turtlebot/workspace/src/turtle_gazebo/launch/warehouse.launch.py#L6)

```python
from launch.substitutions import LaunchConfiguration  # ← 사용되지 않음
```

사용하지 않는 import가 포함되어 있습니다. 명확한 코드를 위해 제거하는 것을 권장합니다.

---

## 🔵 LOW (개선 권장)

### [L-1] `fms_node.py` — `pending_tasks`와 `task_destinations` 로직 위험
작업 완료 후 `self.pending_tasks = self.task_destinations`로 리스트 참조를 복사하면, 원본 리스트가 변경될 때 예상치 못한 동작이 발생합니다. `self.pending_tasks = list(self.task_destinations)`로 명시적 복사를 권장합니다.

  ### [L-2] `bridge_node.cpp` — 클래스명 명명 규칙 불일치
```cpp
class turtleBridgeNode  // camelCase (ROS2 권장: PascalCase)
```
ROS2 C++ 코딩 스타일 가이드에서는 클래스명에 `PascalCase`를 권장합니다. → `TurtleBridgeNode`

### [L-3] `fms_node.py` — `tb4`는 `CHARGING` 상태이나 충전 로직 없음
`fleet_status`에서 `tb4`는 초기 상태가 `CHARGING`이지만, `CHARGING` 상태를 처리하는 로직(충전 완료 후 `IDLE` 전환 등)이 전혀 없어 `tb4`는 영구적으로 작업에 배정되지 않습니다.

### [L-4] `nav2_params.yaml` — `map_server`의 `yaml_filename` 빈 문자열
```yaml
map_server:
  ros__parameters:
    yaml_filename: ""  # ← 맵 파일 경로 미지정
```
맵 파일이 없으면 AMCL 기반 자율 주행이 불가합니다. 맵 파일 경로를 설정하거나 Navigation2를 `map`-less 모드로 명시적으로 구성해야 합니다.

---

## 수정 우선순위 요약

```
1순위 (즉시 수정) → C-2, C-1: 환경변수 KeyError + FileNotFoundError
2순위 (기능 정상화) → H-2: costmap scan 토픽 /scan → scan (상대경로)
                    → H-1: robot_base_frame 프레임 통일
                    → H-5: bridge_node.cpp 빌드 등록
                    → H-6: mujoco models install 추가
3순위 (안전성) → C-3: time.sleep() 제거
4순위 (필수 파일 생성) → C-4: multi_robot_rviz.rviz 파일 생성
5순위 (의존성 정리) → M-1, M-2: package.xml exec_depend 추가
```
