# Multi-Robot Nav2 Code Review & Implementation Plan

코드를 점검한 결과, 로봇들이 다중으로 스폰되고 Nav2가 실행될 때 발생할 수 있는 고질적인 **TF (Transform) 매칭 오류**를 발견했습니다. 

## 🚨 문제 원인: Gazebo 센서 플러그인의 `frame_id` 누락

현재 `spawn_turtlebots.launch.py`의 `_inject_namespace_into_sdf` 함수는 로봇의 바퀴를 굴리는 `diff_drive` 플러그인에만 네임스페이스(`ns/odom`, `ns/base_footprint`)를 주입하고 있습니다. 
하지만 TurtleBot3 모델(SDF)에는 **LiDAR(레이저 스캐너)**와 **IMU(관성 센서)** 플러그인도 존재합니다. 

- `robot_state_publisher`는 `frame_prefix`를 사용해 TF 트리에 `tb1/base_scan`이라는 프레임을 생성합니다.
- 그러나 Gazebo의 LiDAR 센서 플러그인은 SDF 내에 하드코딩된 `<frame_name>base_scan</frame_name>`을 사용하여 메시지를 발행합니다 (네임스페이스가 붙지 않음).
- 그 결과, Nav2의 Costmap은 `base_scan` 프레임에서 들어오는 센서 데이터를 로봇(`tb1/base_footprint`)과 매칭하지 못해(TF Timeout), 장애물을 인식하지 못하거나 내비게이션 자체가 멈추게 됩니다. 이로 인해 같은 코드를 계속 수정하는 것처럼(문제가 해결되지 않은 채) 느껴지셨을 수 있습니다.

## Proposed Changes

이 문제를 해결하기 위해, 임시 SDF 파일을 생성할 때 LiDAR와 IMU 플러그인의 `<frame_name>`에도 네임스페이스가 붙도록 정규식(Regex)을 확장하여 주입하겠습니다.

### 1. `turtle_gazebo/launch/spawn_turtlebots.launch.py`
SDF 텍스트 내에서 `<frame_name>` 태그를 찾아 `ns`를 접두사로 붙이도록 코드를 수정합니다.
#### [MODIFY] [spawn_turtlebots.launch.py](file:///c:/work/turtlebot/workspace/src/turtle_gazebo/launch/spawn_turtlebots.launch.py)

```python
def _inject_namespace_into_sdf(sdf_content: str, ns: str) -> str:
    # 1. diff_drive 플러그인 네임스페이스 주입 (기존 코드)
    plugin_pattern = r'(<plugin\s+name="[^"]*"[^>]*filename="libgazebo_ros_diff_drive\.so"[^>]*>|<plugin\s+name="[^"]*diff_drive[^"]*"[^>]*>)(.*?)(</plugin>)'
    # ... (기존 치환 로직) ...

    # 2. [추가] 모든 센서(LiDAR, IMU 등) 플러그인의 frame_name에 네임스페이스 prefix 추가
    # 예: <frame_name>base_scan</frame_name> -> <frame_name>tb1/base_scan</frame_name>
    import re
    def inject_frame_prefix(match):
        frame = match.group(1)
        # 이미 네임스페이스가 붙어있지 않은 경우에만 붙임
        if not frame.startswith(ns + '/'):
            return f'<frame_name>{ns}/{frame}</frame_name>'
        return match.group(0)

    sdf_content = re.sub(r'<frame_name>(.*?)</frame_name>', inject_frame_prefix, sdf_content)
    
    return sdf_content
```

## Verification Plan

수정 후 다음 사항들을 확인하여 문제가 제대로 해결되었는지 검증할 수 있습니다:
1. `ros2 launch turtle_navigation multi_bringup.launch.py` 실행
2. Rviz2를 켜고, 각 로봇의 `Global Options > Fixed Frame`을 `odom`으로 맞춤
3. 로봇들의 `LaserScan` 데이터를 추가하고 토픽을 `/tb1/scan`으로 설정했을 때 빨간색 점(장애물)이 제자리에 잘 찍히는지 확인
4. Nav2 서버가 에러 없이(Costmap TF Timeout 에러 없이) 구동되는지 터미널 로그 확인
