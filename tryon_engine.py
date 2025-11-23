"""
Модуль для работы с Texel Try-On Diffusion API через RapidAPI
"""
import os
import requests
import logging
from typing import Dict
import base64
from io import BytesIO
from PIL import Image

logger = logging.getLogger("tryon_engine")

class TryOnEngine:
    """Движок для виртуальной примерки одежды через Texel"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        self.api_url = "https://try-on-diffusion.p.rapidapi.com/v1/virtual-tryon"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "try-on-diffusion.p.rapidapi.com",
            "Content-Type": "application/json"
        }
    
    def image_to_base64(self, image_path: str) -> str:
        """Конвертация изображения в base64"""
        try:
            with Image.open(image_path) as img:
                # Конвертируем в RGB если нужно
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Оптимизируем размер
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                return f"data:image/jpeg;base64,{img_str}"
        except Exception as e:
            logger.error(f"Ошибка конвертации изображения: {e}")
            raise
    
    def generate_tryon(
        self, 
        person_image_path: str, 
        garment_image_path: str,
        category: str = "upper_body"
    ) -> Dict:
        """
        Генерация виртуальной примерки
        
        Args:
            person_image_path: путь к фото человека
            garment_image_path: путь к фото одежды
            category: категория одежды (upper_body, lower_body, dresses)
        """
        try:
            logger.info("Генерация примерки через Texel API...")
            
            person_base64 = self.image_to_base64(person_image_path)
            garment_base64 = self.image_to_base64(garment_image_path)
            
            payload = {
                "person_image": person_base64,
                "garment_image": garment_base64,
                "category": category,
                "num_inference_steps": 30,
                "guidance_scale": 2.0
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if "output_image" in result:
                    output_path = "tryon_result.jpg"
                    self._save_base64_image(result["output_image"], output_path)
                    
                    return {
                        "success": True,
                        "output_path": output_path,
                        "message": "Примерка успешно создана!"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Нет выходного изображения в ответе API"
                    }
            else:
                error_msg = f"API вернул код {response.status_code}"
                logger.error(f"{error_msg}: {response.text}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Превышено время ожидания ответа от API"
            }
        except Exception as e:
            logger.error(f"Ошибка генерации примерки: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _save_base64_image(self, base64_str: str, output_path: str):
        """Сохранение base64 изображения в файл"""
        try:
            if "base64," in base64_str:
                base64_str = base64_str.split("base64,")
            
            image_data = base64.b64decode(base64_str)
            
            with open(output_path, "wb") as f:
                f.write(image_data)
            
            logger.info(f"Результат сохранён: {output_path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения изображения: {e}")
            raise
