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
class Template:
    """
    Template cho CCD image processing
    Đơn giản hơn Recipe, chỉ focus vào crop và barcode scan
    """
    name: str
    description: str = ""
    
    # Crop regions - các vùng cần cắt ra (cũng là vùng scan barcode)
    crop_regions: List[CropRegion] = field(default_factory=list)
    
    # Master image info (không lưu ảnh, chỉ lưu info)
    master_image_width: int = 0
    master_image_height: int = 0
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'crop_regions': [r.to_dict() for r in self.crop_regions],
            'master_image_width': self.master_image_width,
            'master_image_height': self.master_image_height,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """Create from dictionary"""
        crop_regions = [CropRegion.from_dict(r) for r in data.get('crop_regions', [])]
        
        # Backward compatibility: migrate old barcode_regions to crop_regions
        if 'barcode_regions' in data and data['barcode_regions']:
            for barcode_region in data['barcode_regions']:
                # Convert barcode region to crop region with scan_barcode=True
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
        
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            crop_regions=crop_regions,
            master_image_width=data.get('master_image_width', 0),
            master_image_height=data.get('master_image_height', 0),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            version=data.get('version', '1.0')
        )
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Template':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def add_crop_region(self, name: str, x: int, y: int, width: int, height: int, scan_barcode: bool = True):
        """Add crop region (cũng là vùng scan barcode nếu scan_barcode=True)"""
        region = CropRegion(name=name, x=x, y=y, width=width, height=height, scan_barcode=scan_barcode)
        self.crop_regions.append(region)
        self.updated_at = datetime.now().isoformat()
    
    def remove_crop_region(self, name: str) -> bool:
        """Remove crop region by name"""
        for i, region in enumerate(self.crop_regions):
            if region.name == name:
                self.crop_regions.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        return False
    
    def get_crop_region(self, name: str) -> Optional[CropRegion]:
        """Get crop region by name"""
        for region in self.crop_regions:
            if region.name == name:
                return region
        return None

