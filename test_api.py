#!/usr/bin/env python3
"""
API 测试脚本 - 测试后端接口是否正常工作
"""
import requests
import json

API_BASE = "http://localhost:5001"


def print_section(title):
    """打印分隔标题"""
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)


def test_health():
    """测试健康检查"""
    print_section("测试 1: 健康检查")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                print("✅ 健康检查通过")
                return True
        
        print("❌ 健康检查失败")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保后端已启动")
        print("   启动命令: cd backend && python app.py")
        return False
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False


def test_default_voices():
    """测试获取默认音色"""
    print_section("测试 2: 获取默认音色")
    try:
        response = requests.get(f"{API_BASE}/api/default-voices", timeout=5)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if data.get("success") and "voices" in data:
                voices = data["voices"]
                if "mini" in voices and "max" in voices:
                    print("✅ 获取默认音色成功")
                    print(f"   - Mini: {voices['mini']['description']}")
                    print(f"   - Max: {voices['max']['description']}")
                    return True
        
        print("❌ 获取默认音色失败")
        return False
    except Exception as e:
        print(f"❌ 获取默认音色失败: {e}")
        return False


def test_static_files():
    """测试静态文件（BGM）"""
    print_section("测试 3: 静态文件（BGM）")
    try:
        for bgm in ["bgm01.wav", "bgm02.wav"]:
            response = requests.head(f"{API_BASE}/static/{bgm}", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {bgm} 可访问")
            else:
                print(f"   ❌ {bgm} 不可访问 (状态码: {response.status_code})")
                return False
        
        print("✅ 静态文件测试通过")
        return True
    except Exception as e:
        print(f"❌ 静态文件测试失败: {e}")
        return False


def run_basic_tests():
    """运行基础测试（不消耗 API 配额）"""
    print("\n" + "🎙️ " * 15)
    print("    MiniMax AI 播客生成器 - API 测试")
    print("🎙️ " * 15)
    
    results = []
    
    # 基础连接测试
    results.append(("健康检查", test_health()))
    results.append(("默认音色", test_default_voices()))
    results.append(("静态文件", test_static_files()))
    
    # 汇总结果
    print_section("测试结果汇总")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name:20s} {status}")
    
    print(f"\n  总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有基础测试通过！后端服务运行正常！")
        print("\n💡 提示: 完整的播客生成测试请通过前端页面进行")
        print("   访问: http://localhost:3000")
    else:
        print(f"\n⚠️  有 {total - passed} 项测试失败，请检查后端服务")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = run_basic_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n\n测试过程出现异常: {e}")
        exit(1)
