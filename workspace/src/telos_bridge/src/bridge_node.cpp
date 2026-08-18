#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
// #include <mujoco/mujoco.h>

class TelosBridgeNode : public rclcpp::Node
{
public:
  TelosBridgeNode()
  : Node("telos_bridge")
  {
    // Gazebo와 MuJoCo 간의 상태를 동기화하기 위한 타이머 및 퍼블리셔/서브스크라이버 설정
    RCLCPP_INFO(this->get_logger(), "Initializing Gazebo-MuJoCo Hybrid Bridge Node");
    
    timer_ = this->create_wall_timer(
      std::chrono::milliseconds(10), // 100Hz 동기화 루프
      std::bind(&TelosBridgeNode::sync_step, this));
  }

private:
  void sync_step()
  {
    // 1. Gazebo에서 터틀봇의 현재 위치(TF) 수신
    // 2. MuJoCo 물리 엔진 스텝 진행 (적재 하중, 서스펜션 계산)
    // 3. 계산된 반작용력/토크 또는 관성 변화를 Gazebo(또는 ROS 제어기)로 피드백
    // RCLCPP_DEBUG(this->get_logger(), "Syncing Gazebo <-> MuJoCo...");
  }

  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TelosBridgeNode>());
  rclcpp::shutdown();
  return 0;
}
