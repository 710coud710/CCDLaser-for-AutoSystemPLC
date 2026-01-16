"""
Test script for Image Test Feature
Kiểm tra xem các thành phần đã được thêm đúng chưa
"""

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_imports():
    """Test các import cần thiết"""
    print("Testing imports...")
    try:
        from app.view.main_view import MainView
        from app.presenter.main_presenter import MainPresenter
        from app.view.image_display_widget import ImageDisplayWidget
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_view_components():
    """Test các component trong MainView"""
    print("\nTesting MainView components...")
    try:
        from app.view.main_view import MainView
        
        # Check if MainView has new methods
        required_methods = [
            '_on_load_test_image_clicked',
            '_on_process_test_image_clicked',
        ]
        
        for method in required_methods:
            if not hasattr(MainView, method):
                print(f"❌ Missing method: {method}")
                return False
            print(f"✅ Method found: {method}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_presenter_components():
    """Test các component trong MainPresenter"""
    print("\nTesting MainPresenter components...")
    try:
        from app.presenter.main_presenter import MainPresenter
        
        # Check if MainPresenter has new methods
        required_methods = [
            'on_test_image_loaded',
            'on_process_test_image_clicked',
        ]
        
        for method in required_methods:
            if not hasattr(MainPresenter, method):
                print(f"❌ Missing method: {method}")
                return False
            print(f"✅ Method found: {method}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_file_structure():
    """Test cấu trúc file"""
    print("\nTesting file structure...")
    
    required_files = [
        'app/view/main_view.py',
        'app/presenter/main_presenter.py',
        'app/view/image_display_widget.py',
        'docs/test-with-image.md',
        'CHANGELOG_IMAGE_TEST.md',
        'README_IMAGE_TEST.md',
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ File exists: {file_path}")
        else:
            print(f"❌ File missing: {file_path}")
            all_exist = False
    
    return all_exist

def test_test_images():
    """Test xem có ảnh test không"""
    print("\nTesting test images...")
    
    test_image_paths = [
        'test/PT524R0655120CGJ.JPEG',
        'recipes_test/images/Test_Recipe_20260107_133420.png',
        'recipes_test/images/Test_Recipe_20260107_133434.png',
    ]
    
    found_count = 0
    for img_path in test_image_paths:
        if os.path.exists(img_path):
            print(f"✅ Test image found: {img_path}")
            found_count += 1
        else:
            print(f"⚠️  Test image not found: {img_path}")
    
    print(f"\nFound {found_count}/{len(test_image_paths)} test images")
    return found_count > 0

def main():
    """Main test function"""
    print("="*60)
    print("Testing Image Test Feature Implementation")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("View Components", test_view_components),
        ("Presenter Components", test_presenter_components),
        ("File Structure", test_file_structure),
        ("Test Images", test_test_images),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Feature is ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

