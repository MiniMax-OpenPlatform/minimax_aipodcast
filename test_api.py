#!/usr/bin/env python3
"""
API测试脚本 - 测试所有后端接口是否正常工作
"""
import requests
import time
import json

API_BASE = "http://localhost:5001/api"

def print_section(title):
    print("\n" + "="*50)
    print(f"  {title}")
    print("="*50)

def test_health():
    """测试健康检查"""
    print_section("测试1: 健康检查")
    try:
        response = requests.get(f"{API_BASE}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        assert response.status_code == 200
        print("✅ 健康检查通过")
        return True
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_default_voices():
    """测试获取默认音色"""
    print_section("测试2: 获取默认音色")
    try:
        response = requests.get(f"{API_BASE}/default-voices")
        print(f"状态码: {response.status_code}")
        voices = response.json()
        print(f"默认音色: {json.dumps(voices, indent=2, ensure_ascii=False)}")
        assert 'mini' in voices and 'max' in voices
        print("✅ 获取默认音色成功")
        return True
    except Exception as e:
        print(f"❌ 获取默认音色失败: {e}")
        return False

def test_parse_topic():
    """测试话题解析"""
    print_section("测试3: 话题解析")
    try:
        data = {
            'type': 'topic',
            'topic': '人工智能的未来发展'
        }
        response = requests.post(f"{API_BASE}/parse-content", data=data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"解析结果: {result.get('content', '')[:100]}...")
        assert result.get('success') == True
        print("✅ 话题解析成功")
        return result.get('content', '')
    except Exception as e:
        print(f"❌ 话题解析失败: {e}")
        return None

def test_generate_cover():
    """测试封面生成"""
    print_section("测试4: 封面生成")
    try:
        data = {
            'content': '这是一个关于人工智能的播客节目',
            'topic': '人工智能的未来'
        }
        response = requests.post(
            f"{API_BASE}/generate-cover",
            json=data,
            timeout=30
        )
        print(f"状态码: {response.status_code}")
        result = response.json()
        
        if result.get('success'):
            print(f"封面URL: {result.get('image_url', '')[:80]}...")
            print(f"文本Trace-ID: {result.get('text_trace_id')}")
            print(f"图片Trace-ID: {result.get('image_trace_id')}")
            print("✅ 封面生成成功")
            return True
        else:
            print(f"⚠️  封面生成失败: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ 封面生成测试失败: {e}")
        return False

def test_welcome_audio():
    """测试欢迎音频生成"""
    print_section("测试5: 欢迎音频生成")
    try:
        response = requests.get(f"{API_BASE}/welcome-audio", timeout=20)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"音频URL: {result.get('audio_url')}")
        print(f"Trace-ID: {result.get('trace_id')}")
        print("✅ 欢迎音频生成成功")
        return True
    except Exception as e:
        print(f"❌ 欢迎音频生成失败: {e}")
        return False

def test_bgm():
    """测试BGM获取"""
    print_section("测试6: BGM获取")
    try:
        for bgm_name in ['bgm01', 'bgm02']:
            response = requests.get(f"{API_BASE}/bgm/{bgm_name}")
            print(f"{bgm_name} 状态码: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ {bgm_name} 可用")
            else:
                print(f"  ❌ {bgm_name} 不可用")
        return True
    except Exception as e:
        print(f"❌ BGM测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("\n" + "🎙️"*20)
    print("    AI播客生成器 - API测试套件")
    print("🎙️"*20)
    
    results = []
    
    # 基础测试
    results.append(("健康检查", test_health()))
    time.sleep(1)
    
    results.append(("默认音色", test_default_voices()))
    time.sleep(1)
    
    results.append(("BGM获取", test_bgm()))
    time.sleep(1)
    
    results.append(("话题解析", test_parse_topic() is not None))
    time.sleep(1)
    
    # API调用测试（这些会消耗API配额，谨慎运行）
    print("\n⚠️  以下测试会调用MiniMax API，消耗配额")
    response = input("是否继续？(y/n): ")
    
    if response.lower() == 'y':
        results.append(("欢迎音频", test_welcome_audio()))
        time.sleep(2)
        
        results.append(("封面生成", test_generate_cover()))
        time.sleep(2)
    
    # 汇总结果
    print_section("测试结果汇总")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:20s} {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统运行正常！")
    else:
        print(f"\n⚠️  有 {total - passed} 项测试失败，请检查")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n\n测试过程出现异常: {e}")
        exit(1)



