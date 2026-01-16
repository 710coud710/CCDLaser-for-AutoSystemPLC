"""
Test script for Template System
Kiểm tra xem Template System đã được implement đúng chưa
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
        from app.model.template_data import Template, CropRegion, BarcodeRegion, TemplateService
        from app.view.main_view import MainView
        from app.presenter.main_presenter import MainPresenter
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_template_model():
    """Test Template model"""
    print("\nTesting Template model...")
    try:
        from app.model.template_data import Template, CropRegion, BarcodeRegion
        
        # Create template
        template = Template(name="Test_Template", description="Test")
        
        # Add regions
        template.add_crop_region("Crop1", 100, 100, 200, 200)
        template.add_barcode_region("Barcode1", 300, 300, 150, 150)
        
        # Check
        assert len(template.crop_regions) == 1
        assert len(template.barcode_regions) == 1
        assert template.crop_regions[0].name == "Crop1"
        assert template.barcode_regions[0].name == "Barcode1"
        
        # JSON serialization
        json_str = template.to_json()
        template2 = Template.from_json(json_str)
        assert template2.name == template.name
        assert len(template2.crop_regions) == 1
        
        print("✅ Template model works")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_template_service():
    """Test TemplateService"""
    print("\nTesting TemplateService...")
    try:
        from app.model.template_data import TemplateService, Template
        
        # Create service
        service = TemplateService()
        
        # Check templates directory
        templates_dir = service.templates_dir
        print(f"   Templates directory: {templates_dir}")
        assert os.path.exists(templates_dir)
        
        # List templates
        templates = service.list_templates()
        print(f"   Found {len(templates)} template(s)")
        
        print("✅ TemplateService works")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_view_components():
    """Test MainView components"""
    print("\nTesting MainView components...")
    try:
        from app.view.main_view import MainView
        
        # Check if MainView has template mode methods
        required_methods = [
            '_on_template_load_image_clicked',
            '_on_add_crop_region_clicked',
            '_on_add_barcode_region_clicked',
            '_on_save_template_clicked',
            '_on_load_template_clicked',
            '_on_refresh_templates_clicked',
            '_on_template_load_test_image_clicked',
            '_on_process_template_clicked',
            'update_template_list',
            'update_template_regions_list',
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
    """Test MainPresenter components"""
    print("\nTesting MainPresenter components...")
    try:
        from app.presenter.main_presenter import MainPresenter
        
        # Check if MainPresenter has template mode methods
        required_methods = [
            'on_template_image_loaded',
            'on_template_crop_region_added',
            'on_template_barcode_region_added',
            'on_save_template_clicked',
            'on_load_template_clicked',
            'on_refresh_templates_clicked',
            'on_template_test_image_loaded',
            'on_process_template_clicked',
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
        'app/model/template_data/__init__.py',
        'app/model/template_data/template_model.py',
        'app/model/template_data/template_service.py',
        'docs/template-system-guide.md',
        'TEMPLATE_SYSTEM_README.md',
        'HUONG_DAN_TEMPLATE.txt',
        'TEMPLATE_SYSTEM_SUMMARY.md',
        'TEMPLATE_SYSTEM_FILES.txt',
        'FINAL_SUMMARY_TEMPLATE.md',
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ File exists: {file_path}")
        else:
            print(f"❌ File missing: {file_path}")
            all_exist = False
    
    return all_exist


def main():
    """Main test function"""
    print("="*60)
    print("Testing Template System Implementation")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Template Model", test_template_model),
        ("Template Service", test_template_service),
        ("View Components", test_view_components),
        ("Presenter Components", test_presenter_components),
        ("File Structure", test_file_structure),
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
        print("\n🎉 All tests passed! Template System is ready to use.")
        print("\n📚 Next steps:")
        print("   1. Read HUONG_DAN_TEMPLATE.txt for usage guide")
        print("   2. Run the application: python main.py")
        print("   3. Go to 'Template Mode' tab")
        print("   4. Try creating your first template!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

