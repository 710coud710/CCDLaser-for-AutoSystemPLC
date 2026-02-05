"""
Template Data Model
Định nghĩa cấu trúc template cho CCD image processing
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import json
from datetime import datetime


@dataclass
class CropRegion:
    """Vùng cắt ảnh - cũng là vùng scan barcode (dùng chung)"""
    name: str
    x: int
    y: int
    width: int
    height: int
    enabled: bool = True
    scan_barcode: bool = True  # Có scan barcode trong vùng này không
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CropRegion':
        # Backward compatibility: nếu không có scan_barcode, mặc định True
        if 'scan_barcode' not in data:
            data['scan_barcode'] = True
        return cls(**data)


@dataclass
class CCD1Config:
    """Cấu hình cho CCD1 (ROI Template Matching)"""
    enabled: bool = False  # Có sử dụng CCD1 cho template này không
    roi_x: int = 0
    roi_y: int = 0
    roi_width: int = 0
    roi_height: int = 0
    match_threshold: float = 0.8  # Ngưỡng so sánh template
    template_image_path: str = ""  # Đường dẫn đến ảnh template
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CCD1Config':
        return cls(**data)


@dataclass
class CCD2Config:
    """Cấu hình cho CCD2 (Datamatrix Scanning)"""
    enabled: bool = False  # Có sử dụng CCD2 cho template này không
    crop_regions: List[CropRegion] = field(default_factory=list)  # Regions để scan datamatrix
    master_image_width: int = 0
    master_image_height: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'crop_regions': [r.to_dict() for r in self.crop_regions],
            'master_image_width': self.master_image_width,
            'master_image_height': self.master_image_height
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CCD2Config':
        crop_regions = [CropRegion.from_dict(r) for r in data.get('crop_regions', [])]
        return cls(
            enabled=data.get('enabled', False),
            crop_regions=crop_regions,
            master_image_width=data.get('master_image_width', 0),
            master_image_height=data.get('master_image_height', 0)
        )


@dataclass
class Template:
    """
    Template cho CCD image processing - HỖ TRỢ CẢ CCD1 VÀ CCD2
    - CCD1: ROI Template Matching
    - CCD2: Datamatrix Scanning với regions
    """
    name: str
    description: str = ""
    
    # CCD1 Configuration
    ccd1_config: CCD1Config = field(default_factory=CCD1Config)
    
    # CCD2 Configuration
    ccd2_config: CCD2Config = field(default_factory=CCD2Config)
    
    # Legacy fields (để backward compatibility với CCD2)
    crop_regions: List[CropRegion] = field(default_factory=list)
    master_image_width: int = 0
    master_image_height: int = 0
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "2.0"  # Version 2.0 hỗ trợ cả CCD1 và CCD2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'ccd1_config': self.ccd1_config.to_dict(),
            'ccd2_config': self.ccd2_config.to_dict(),
            # Legacy fields
            'crop_regions': [r.to_dict() for r in self.crop_regions],
            'master_image_width': self.master_image_width,
            'master_image_height': self.master_image_height,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """Create from dictionary with backward compatibility"""
        version = data.get('version', '1.0')
        
        # Load CCD1 config
        ccd1_config = CCD1Config.from_dict(data.get('ccd1_config', {})) if 'ccd1_config' in data else CCD1Config()
        
        # Load CCD2 config
        if 'ccd2_config' in data:
            ccd2_config = CCD2Config.from_dict(data['ccd2_config'])
        else:
            # Backward compatibility: migrate old crop_regions to ccd2_config
            crop_regions = [CropRegion.from_dict(r) for r in data.get('crop_regions', [])]
            
            # Migrate old barcode_regions to crop_regions
            if 'barcode_regions' in data and data['barcode_regions']:
                for barcode_region in data['barcode_regions']:
                    crop_region = CropRegion(
                        name=barcode_region.get('name', ''),
                        x=barcode_region.get('x', 0),
                        y=barcode_region.get('y', 0),
                        width=barcode_region.get('width', 0),
                        height=barcode_region.get('height', 0),
                        enabled=barcode_region.get('enabled', True),
                        scan_barcode=True
                    )
                    crop_regions.append(crop_region)
            
            ccd2_config = CCD2Config(
                enabled=len(crop_regions) > 0,  # Auto-enable nếu có regions
                crop_regions=crop_regions,
                master_image_width=data.get('master_image_width', 0),
                master_image_height=data.get('master_image_height', 0)
            )
        
        # Legacy crop_regions (for backward compatibility)
        legacy_crop_regions = [CropRegion.from_dict(r) for r in data.get('crop_regions', [])]
        
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            ccd1_config=ccd1_config,
            ccd2_config=ccd2_config,
            crop_regions=legacy_crop_regions,
            master_image_width=data.get('master_image_width', 0),
            master_image_height=data.get('master_image_height', 0),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            version=version
        )
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Template':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    # ============ CCD1 Methods ============
    def set_ccd1_roi(self, x: int, y: int, width: int, height: int, threshold: float = 0.8):
        """Set ROI cho CCD1"""
        self.ccd1_config.roi_x = x
        self.ccd1_config.roi_y = y
        self.ccd1_config.roi_width = width
        self.ccd1_config.roi_height = height
        self.ccd1_config.match_threshold = threshold
        self.ccd1_config.enabled = True
        self.updated_at = datetime.now().isoformat()
    
    def set_ccd1_template_image(self, image_path: str):
        """Set template image path cho CCD1"""
        self.ccd1_config.template_image_path = image_path
        self.updated_at = datetime.now().isoformat()
    
    # ============ CCD2 Methods ============
    def add_ccd2_region(self, name: str, x: int, y: int, width: int, height: int, scan_barcode: bool = True):
        """Add region cho CCD2"""
        region = CropRegion(name=name, x=x, y=y, width=width, height=height, scan_barcode=scan_barcode)
        self.ccd2_config.crop_regions.append(region)
        self.ccd2_config.enabled = True
        self.updated_at = datetime.now().isoformat()
    
    def remove_ccd2_region(self, name: str) -> bool:
        """Remove region from CCD2"""
        for i, region in enumerate(self.ccd2_config.crop_regions):
            if region.name == name:
                self.ccd2_config.crop_regions.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        return False
    
    def get_ccd2_region(self, name: str) -> Optional[CropRegion]:
        """Get region from CCD2 by name"""
        for region in self.ccd2_config.crop_regions:
            if region.name == name:
                return region
        return None
    
    def set_ccd2_master_image_size(self, width: int, height: int):
        """Set master image size cho CCD2"""
        self.ccd2_config.master_image_width = width
        self.ccd2_config.master_image_height = height
        self.updated_at = datetime.now().isoformat()
    
    # ============ Legacy Methods (for backward compatibility) ============
    def add_crop_region(self, name: str, x: int, y: int, width: int, height: int, scan_barcode: bool = True):
        """Legacy method - adds to both legacy list and CCD2 config"""
        region = CropRegion(name=name, x=x, y=y, width=width, height=height, scan_barcode=scan_barcode)
        self.crop_regions.append(region)
        # Also add to CCD2 config
        self.ccd2_config.crop_regions.append(region)
        self.ccd2_config.enabled = True
        self.updated_at = datetime.now().isoformat()
    
    def remove_crop_region(self, name: str) -> bool:
        """Legacy method - removes from both legacy list and CCD2 config"""
        removed = False
        for i, region in enumerate(self.crop_regions):
            if region.name == name:
                self.crop_regions.pop(i)
                removed = True
                break
        # Also remove from CCD2 config
        for i, region in enumerate(self.ccd2_config.crop_regions):
            if region.name == name:
                self.ccd2_config.crop_regions.pop(i)
                break
        if removed:
            self.updated_at = datetime.now().isoformat()
        return removed
    
    def get_crop_region(self, name: str) -> Optional[CropRegion]:
        """Legacy method - gets from legacy list first, then CCD2 config"""
        for region in self.crop_regions:
            if region.name == name:
                return region
        for region in self.ccd2_config.crop_regions:
            if region.name == name:
                return region
        return None

