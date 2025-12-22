# Layout Project

```bash

CCDLaser/
│
├─ main.py
│
├─ app/
│   ├─ presenter/
│   │   ├─ main_presenter.py
│   │   └─ state_machine.py
│   │
│   ├─ view/
│   │   ├─ main_view.py
│   │   └─ view_interface.py
│   │
│   └─ model/
│       ├─ camera/                      #xử lý mở camera
│       │   ├─ camera_base.py
│       │   ├─ mindvision_camera.py
│       │   ├─ camera_connection_service.py  ← OPEN / CLOSE ở đây
│       │   └─ mock_camera.py
│       │
│       ├─ image/                       #Xử lý liên quan đến ảnh
│       │   ├─ image_processor.py
│       │   └─ roi_config.py
│       │
│       ├─ qr/
│       │   ├─ qr_decoder.py
│       │   └─ qr_result.py
│       │
│       ├─ sn/
│       │   ├─ sn_validator.py
│       │   └─ sn_rule.py
│       │
│       └─ domain/
│           ├─ capture_result.py
│           └─ app_status.py
│
├─ services/
│   ├─ logger_service.py
│   └─ config_service.py
│
├─ setting/
│   ├─ camera.yaml
│   ├─ qr.yaml
│   └─ app.yaml
│
├─ assets/
│   └─ test_images/
│
├─ tests/
│   ├─ test_qr_decode.py
│   └─ test_sn_validate.py
│
└─ requirements.txt

```