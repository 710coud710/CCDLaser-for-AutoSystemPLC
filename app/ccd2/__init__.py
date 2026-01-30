"""
CCD2 Module - Độc lập hoàn toàn với CCD1
Chứa model, view, presenter riêng cho camera CCD2
"""
from .model.ccd2_camera_service import CCD2CameraService
from .view.ccd2_view import CCD2View
from .presenter.ccd2_presenter import CCD2Presenter

__all__ = ['CCD2CameraService', 'CCD2View', 'CCD2Presenter']
