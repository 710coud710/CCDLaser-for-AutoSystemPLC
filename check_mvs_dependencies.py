"""
Check MVS SDK Dependencies
Script kiểm tra xem có đầy đủ dependencies để chạy MVS SDK không
"""
import os
import sys
import platform

def check_python_version():
    """Check Python version"""
    print("=" * 60)
    print("1. CHECKING PYTHON VERSION")
    print("=" * 60)
    
    print(f"Python version: {sys.version}")
    print(f"Architecture: {platform.architecture()[0]}")
    
    if platform.architecture()[0] != '64bit':
        print("❌ ERROR: MVS SDK requires Python 64-bit!")
        print("   Current Python is 32-bit")
        return False
    else:
        print("✓ Python 64-bit OK")
        return True


def check_mvs_runtime():
    """Check MVS Runtime installation"""
    print("\n" + "=" * 60)
    print("2. CHECKING MVS RUNTIME")
    print("=" * 60)
    
    possible_paths = [
        r"C:\Program Files\MVS\Runtime\Win64_x64",
        r"C:\Program Files\MVS\Runtime\Win64",
        r"C:\Program Files (x86)\MVS\Runtime\Win64_x64",
        r"C:\Program Files (x86)\MVS\Runtime\Win64",
    ]
    
    found = False
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✓ Found MVS Runtime: {path}")
            
            # Check important DLL files
            required_dlls = [
                "MvCameraControl.dll",
                "MVGigEVisionSDK.dll",
                "MVUSB3VisionSDK.dll",
            ]
            
            print(f"\n  Checking DLLs in {path}:")
            all_found = True
            for dll in required_dlls:
                dll_path = os.path.join(path, dll)
                if os.path.exists(dll_path):
                    print(f"    ✓ {dll}")
                else:
                    print(f"    ❌ {dll} NOT FOUND")
                    all_found = False
            
            found = True
            
            # Check if in PATH
            path_env = os.environ.get('PATH', '')
            if path in path_env:
                print(f"\n  ✓ MVS Runtime is in PATH")
            else:
                print(f"\n  ⚠️  MVS Runtime NOT in PATH")
                print(f"     Add this to PATH: {path}")
                print(f"     Sau đó RESTART máy!")
            
            break
    
    if not found:
        print("❌ MVS Runtime NOT FOUND!")
        print("\nSolutions:")
        print("1. Cài đặt MVS SDK từ Hikvision")
        print("2. Hoặc copy folder Runtime vào C:\\Program Files\\MVS\\")
        return False
    
    return True


def check_local_dll():
    """Check DLL in project folder"""
    print("\n" + "=" * 60)
    print("3. CHECKING LOCAL DLL")
    print("=" * 60)
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    dll_path = os.path.join(project_root, "MvCameraControl.dll")
    
    if os.path.exists(dll_path):
        print(f"✓ Found local DLL: {dll_path}")
        file_size = os.path.getsize(dll_path)
        print(f"  Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        print("\n⚠️  WARNING:")
        print("  Chỉ có MvCameraControl.dll KHÔNG ĐỦ!")
        print("  Cần toàn bộ MVS Runtime với tất cả dependencies!")
        return True
    else:
        print("❌ Local MvCameraControl.dll NOT FOUND")
        return False


def check_mvimport():
    """Check MvImport folder"""
    print("\n" + "=" * 60)
    print("4. CHECKING MvImport FOLDER")
    print("=" * 60)
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    mvimport_path = os.path.join(project_root, "MvImport")
    
    if not os.path.exists(mvimport_path):
        print(f"❌ MvImport folder NOT FOUND: {mvimport_path}")
        return False
    
    print(f"✓ Found MvImport: {mvimport_path}")
    
    required_files = [
        "MvCameraControl_class.py",
        "CameraParams_header.py",
        "MvErrorDefine_const.py",
        "PixelType_header.py",
    ]
    
    print("\n  Checking required files:")
    all_found = True
    for file in required_files:
        file_path = os.path.join(mvimport_path, file)
        if os.path.exists(file_path):
            print(f"    ✓ {file}")
        else:
            print(f"    ❌ {file} NOT FOUND")
            all_found = False
    
    return all_found


def test_import():
    """Try to import MVS SDK"""
    print("\n" + "=" * 60)
    print("5. TESTING IMPORT")
    print("=" * 60)
    
    try:
        # Add MvImport to path
        project_root = os.path.dirname(os.path.abspath(__file__))
        mvimport_path = os.path.join(project_root, "MvImport")
        if mvimport_path not in sys.path:
            sys.path.insert(0, mvimport_path)
        
        # Add DLL paths
        dll_paths = [
            project_root,
            r"C:\Program Files\MVS\Runtime\Win64_x64",
            r"C:\Program Files\MVS\Runtime\Win64",
        ]
        
        for dll_path in dll_paths:
            if os.path.exists(dll_path):
                current_path = os.environ.get('PATH', '')
                if dll_path not in current_path:
                    os.environ['PATH'] = dll_path + os.pathsep + current_path
        
        print("Attempting to import MvCamera...")
        from MvCameraControl_class import MvCamera
        print("✓ Import SUCCESS!")
        
        # Try to initialize
        print("\nAttempting to initialize SDK...")
        ret = MvCamera.MV_CC_Initialize()
        print(f"✓ Initialize SDK returned: {ret}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import FAILED!")
        print(f"Error: {e}")
        print(f"\nError type: {type(e).__name__}")
        
        if "DLL" in str(e):
            print("\n💡 SOLUTION:")
            print("1. Cài đặt MVS SDK đầy đủ")
            print("2. Thêm vào PATH: C:\\Program Files\\MVS\\Runtime\\Win64_x64")
            print("3. RESTART máy sau khi thêm PATH")
            print("4. Chạy lại script này để verify")
        
        return False


def print_solution():
    """Print solution steps"""
    print("\n" + "=" * 60)
    print("📋 SOLUTION - CÁC BƯỚC SỬA LỖI")
    print("=" * 60)
    
    print("""
NGUYÊN NHÂN:
- MvCameraControl.dll cần NHIỀU DLL khác từ MVS Runtime
- Chỉ copy 1 file DLL KHÔNG ĐỦ!
- Cần toàn bộ MVS Runtime với tất cả dependencies

GIẢI PHÁP:

Option 1: CÀI MVS SDK ĐẦY ĐỦ (KHUYÊN DÙNG)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Download MVS SDK từ Hikvision
2. Cài đặt MVS SDK (bản Windows 64-bit)
3. Sau khi cài, MVS sẽ tạo folder:
   C:\\Program Files\\MVS\\Runtime\\Win64_x64\\
4. Thêm folder này vào PATH:
   - Control Panel → System → Advanced → Environment Variables
   - Trong System Variables, chọn Path → Edit → New
   - Thêm: C:\\Program Files\\MVS\\Runtime\\Win64_x64
   - Click OK
5. RESTART MÁY (QUAN TRỌNG!)
6. Chạy lại: python check_mvs_dependencies.py

Option 2: COPY TOÀN BỘ RUNTIME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Nếu có MVS đã cài ở máy khác:
   - Copy toàn bộ folder: C:\\Program Files\\MVS\\Runtime\\Win64_x64\\
   - Paste vào project: d:\\Beta\\CCDLaser\\mvs_runtime\\
2. Script sẽ tự động tìm DLL trong folder này

Option 3: DÙNG MINDVISION SDK (FALLBACK)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nếu không thể cài MVS, quay lại dùng MindVision:
1. Mở: setting/camera.yaml
2. Sửa: camera_type: "mindvision"
3. Restart app

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERIFY:
Sau khi làm xong, chạy:
  python check_mvs_dependencies.py
  
Nếu tất cả ✓ → chạy:
  python test_mvs_camera.py
""")


def main():
    """Main check function"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "MVS SDK DEPENDENCIES CHECKER" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Check Python
    results.append(("Python 64-bit", check_python_version()))
    
    # Check MVS Runtime
    results.append(("MVS Runtime", check_mvs_runtime()))
    
    # Check local DLL
    results.append(("Local DLL", check_local_dll()))
    
    # Check MvImport
    results.append(("MvImport folder", check_mvimport()))
    
    # Test import
    results.append(("Import test", test_import()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{name:20s} : {status}")
    
    all_pass = all(result for _, result in results)
    
    if all_pass:
        print("\n✓✓✓ ALL CHECKS PASSED!")
        print("MVS SDK is ready to use!")
        print("\nNext step:")
        print("  python test_mvs_camera.py")
    else:
        print("\n❌ SOME CHECKS FAILED")
        print_solution()
    
    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
