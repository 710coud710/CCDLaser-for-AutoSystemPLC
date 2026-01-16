"""
Recipe Service - Quản lý bản mẫu (Recipe-based Vision)
Lưu trữ template image, template region, và QR ROI regions
"""
import cv2
import numpy as np
import json
import os
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class TemplateRegion:
    """Vùng định vị (Template Region) - dùng để so khớp vị trí panel"""
    x: int
    y: int
    width: int
    height: int
    name: str = "Template"
    
    def get_roi(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Extract ROI từ image"""
        h, w = image.shape[:2]
        x1 = max(0, self.x)
        y1 = max(0, self.y)
        x2 = min(w, self.x + self.width)
        y2 = min(h, self.y + self.height)
        
        if x2 <= x1 or y2 <= y1:
            return None
        
        return image[y1:y2, x1:x2].copy()


@dataclass
class QRROIRegion:
    """Vùng QR/DataMatrix - lưu theo tọa độ TƯƠNG ĐỐI với template"""
    name: str
    enabled: bool
    # Tọa độ tương đối với template region
    relative_x: int
    relative_y: int
    width: int
    height: int
    
    def get_absolute_coords(self, template_x: int, template_y: int) -> Tuple[int, int, int, int]:
        """Chuyển đổi sang tọa độ tuyệt đối trên ảnh"""
        abs_x = template_x + self.relative_x
        abs_y = template_y + self.relative_y
        return abs_x, abs_y, self.width, self.height
    
    def transform_coords(self, dx: int, dy: int, angle: float = 0.0) -> Tuple[int, int, int, int]:
        """
        Transform ROI coordinates theo offset và góc xoay
        Args:
            dx, dy: Độ lệch vị trí (pixel)
            angle: Góc xoay (độ)
        Returns:
            (x, y, w, h) đã transform
        """
        # TODO: Implement rotation transform nếu cần
        # Hiện tại chỉ áp dụng translation
        new_x = self.relative_x + dx
        new_y = self.relative_y + dy
        return new_x, new_y, self.width, self.height


@dataclass
class Tolerance:
    """Ngưỡng sai lệch cho phép"""
    max_dx: float = 10.0  # pixel
    max_dy: float = 10.0  # pixel
    max_angle: float = 2.0  # degree
    min_match_score: float = 0.7  # Template matching score threshold


@dataclass
class Recipe:
    """
    Recipe - Bản mẫu cho một loại panel
    Chứa:
    - Template image (ảnh master)
    - Template region (vùng định vị)
    - QR ROI regions (các vùng QR, tọa độ tương đối)
    - Tolerance (ngưỡng sai lệch)
    """
    name: str
    description: str
    created_at: str
    template_image_path: str  # Path to master image
    template_region: TemplateRegion
    qr_roi_regions: List[QRROIRegion]
    tolerance: Tolerance
    
    # Runtime data (không lưu vào file)
    _template_image: Optional[np.ndarray] = None
    _template_roi: Optional[np.ndarray] = None
    
    def load_template_image(self) -> bool:
        """Load template image từ file"""
        try:
            if not os.path.exists(self.template_image_path):
                logger.error(f"Template image not found: {self.template_image_path}")
                return False
            
            self._template_image = cv2.imread(self.template_image_path)
            if self._template_image is None:
                logger.error(f"Failed to load template image: {self.template_image_path}")
                return False
            
            # Extract template ROI
            self._template_roi = self.template_region.get_roi(self._template_image)
            if self._template_roi is None:
                logger.error("Failed to extract template ROI")
                return False
            
            logger.info(f"Template image loaded: {self.template_image_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading template image: {e}")
            return False
    
    def get_template_image(self) -> Optional[np.ndarray]:
        """Get template image (load nếu chưa load)"""
        if self._template_image is None:
            self.load_template_image()
        return self._template_image
    
    def get_template_roi(self) -> Optional[np.ndarray]:
        """Get template ROI (load nếu chưa load)"""
        if self._template_roi is None:
            self.load_template_image()
        return self._template_roi
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (để lưu JSON)"""
        return {
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at,
            'template_image_path': self.template_image_path,
            'template_region': asdict(self.template_region),
            'qr_roi_regions': [asdict(roi) for roi in self.qr_roi_regions],
            'tolerance': asdict(self.tolerance)
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Recipe':
        """Create Recipe from dictionary"""
        template_region = TemplateRegion(**data['template_region'])
        qr_roi_regions = [QRROIRegion(**roi) for roi in data['qr_roi_regions']]
        tolerance = Tolerance(**data.get('tolerance', {}))
        
        return Recipe(
            name=data['name'],
            description=data['description'],
            created_at=data['created_at'],
            template_image_path=data['template_image_path'],
            template_region=template_region,
            qr_roi_regions=qr_roi_regions,
            tolerance=tolerance
        )


class RecipeService:
    """
    Recipe Service - Quản lý recipes
    - Tạo recipe mới từ ảnh master
    - Lưu/Load recipe
    - Quản lý danh sách recipes
    """
    
    def __init__(self, recipe_dir: str = "recipes"):
        self.recipe_dir = recipe_dir
        self.image_dir = os.path.join(recipe_dir, "images")
        self.config_dir = os.path.join(recipe_dir, "configs")
        
        # Tạo thư mục nếu chưa có
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Current active recipe
        self.current_recipe: Optional[Recipe] = None
        
        logger.info(f"RecipeService initialized: {self.recipe_dir}")
    
    def create_recipe(
        self,
        name: str,
        description: str,
        master_image: np.ndarray,
        template_region: TemplateRegion,
        qr_roi_regions: List[QRROIRegion],
        tolerance: Optional[Tolerance] = None
    ) -> Optional[Recipe]:
        """
        Tạo recipe mới từ ảnh master
        
        Args:
            name: Tên recipe
            description: Mô tả
            master_image: Ảnh master (panel chuẩn)
            template_region: Vùng định vị
            qr_roi_regions: Các vùng QR
            tolerance: Ngưỡng sai lệch (None = dùng default)
        
        Returns:
            Recipe object hoặc None nếu lỗi
        """
        try:
            # Validate inputs
            if master_image is None or master_image.size == 0:
                logger.error("Invalid master image")
                return None
            
            if template_region.width <= 0 or template_region.height <= 0:
                logger.error("Invalid template region")
                return None
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = name.replace(" ", "_").replace("/", "_")
            image_filename = f"{safe_name}_{timestamp}.png"
            image_path = os.path.join(self.image_dir, image_filename)
            
            # Save master image
            cv2.imwrite(image_path, master_image)
            logger.info(f"Master image saved: {image_path}")
            
            # Create recipe
            recipe = Recipe(
                name=name,
                description=description,
                created_at=datetime.now().isoformat(),
                template_image_path=image_path,
                template_region=template_region,
                qr_roi_regions=qr_roi_regions,
                tolerance=tolerance or Tolerance()
            )
            
            # Load template image
            if not recipe.load_template_image():
                logger.error("Failed to load template image")
                return None
            
            # Save recipe config
            if not self.save_recipe(recipe):
                logger.error("Failed to save recipe config")
                return None
            
            logger.info(f"Recipe created: {name}")
            return recipe
            
        except Exception as e:
            logger.error(f"Error creating recipe: {e}", exc_info=True)
            return None
    
    def save_recipe(self, recipe: Recipe) -> bool:
        """Lưu recipe vào file JSON"""
        try:
            safe_name = recipe.name.replace(" ", "_").replace("/", "_")
            config_filename = f"{safe_name}.json"
            config_path = os.path.join(self.config_dir, config_filename)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(recipe.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Recipe saved: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving recipe: {e}", exc_info=True)
            return False
    
    def load_recipe(self, recipe_name: str) -> Optional[Recipe]:
        """Load recipe từ file"""
        try:
            safe_name = recipe_name.replace(" ", "_").replace("/", "_")
            config_filename = f"{safe_name}.json"
            config_path = os.path.join(self.config_dir, config_filename)
            
            if not os.path.exists(config_path):
                logger.error(f"Recipe config not found: {config_path}")
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            recipe = Recipe.from_dict(data)
            
            # Load template image
            if not recipe.load_template_image():
                logger.error("Failed to load template image")
                return None
            
            logger.info(f"Recipe loaded: {recipe_name}")
            return recipe
            
        except Exception as e:
            logger.error(f"Error loading recipe: {e}", exc_info=True)
            return None
    
    def list_recipes(self) -> List[str]:
        """Liệt kê tất cả recipes có sẵn"""
        try:
            if not os.path.exists(self.config_dir):
                return []
            
            recipes = []
            for filename in os.listdir(self.config_dir):
                if filename.endswith('.json'):
                    recipe_name = filename[:-5]  # Remove .json
                    recipes.append(recipe_name)
            
            return sorted(recipes)
            
        except Exception as e:
            logger.error(f"Error listing recipes: {e}")
            return []
    
    def delete_recipe(self, recipe_name: str) -> bool:
        """Xóa recipe"""
        try:
            # Load recipe để lấy image path
            recipe = self.load_recipe(recipe_name)
            if recipe is None:
                logger.warning(f"Recipe not found: {recipe_name}")
                return False
            
            # Delete image file
            if os.path.exists(recipe.template_image_path):
                os.remove(recipe.template_image_path)
                logger.info(f"Deleted image: {recipe.template_image_path}")
            
            # Delete config file
            safe_name = recipe_name.replace(" ", "_").replace("/", "_")
            config_path = os.path.join(self.config_dir, f"{safe_name}.json")
            if os.path.exists(config_path):
                os.remove(config_path)
                logger.info(f"Deleted config: {config_path}")
            
            logger.info(f"Recipe deleted: {recipe_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting recipe: {e}", exc_info=True)
            return False
    
    def set_current_recipe(self, recipe: Recipe):
        """Set recipe hiện tại đang sử dụng"""
        self.current_recipe = recipe
        logger.info(f"Current recipe set: {recipe.name}")
    
    def get_current_recipe(self) -> Optional[Recipe]:
        """Get recipe hiện tại"""
        return self.current_recipe


