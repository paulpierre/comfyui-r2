import os
import hashlib
import json
import requests
from typing import Optional, Tuple
import logging

from PIL import Image
import comfy.utils
from nodes import NODE_CLASS_MAPPINGS, SOCKET_TYPES

# Set up logging
logger = logging.getLogger('R2BucketUploadNode')
logger.setLevel(logging.INFO)

# Ensure that r2client is installed
try:
    from r2client.R2Client import R2Client
except ImportError:
    logger.info("r2client not found, attempting to install...")
    try:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "r2client==0.2.1"])
        from r2client.R2Client import R2Client
        logger.info("Successfully installed r2client")
    except Exception as e:
        logger.error(f"Failed to install r2client: {str(e)}")
        raise

class R2BucketUploadNode:
    CATEGORY = "utils"
    CATEGORY_DISPLAY_NAME = "🪣 R2 Storage"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": ("STRING", {"multiline": True}),
                "negative_prompt": ("STRING", {"multiline": True}),
                "model": ("STRING", {"multiline": False}),
                "slack_webhook_url": ("STRING", {"default": os.getenv("SLACK_WEBHOOK_URL", ""), "multiline": False}),
                "r2_access_key_id": ("STRING", {"default": os.getenv("R2_ACCESS_KEY_ID", ""), "multiline": False}),
                "r2_secret_access_key": ("STRING", {"default": os.getenv("R2_SECRET_ACCESS_KEY", ""), "multiline": False}),
                "r2_upload_path": ("STRING", {"default": os.getenv("R2_UPLOAD_PATH", "assets"), "multiline": False}),
                "r2_endpoint": ("STRING", {"default": os.getenv("R2_ENDPOINT", ""), "multiline": False}),
                "r2_bucket_name": ("STRING", {"default": os.getenv("R2_BUCKET_NAME", ""), "multiline": False}),
                "r2_domain": ("STRING", {"default": os.getenv("R2_DOMAIN", ""), "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")  # Returning image_url and prompt_url
    RETURN_NAMES = ("Image URL", "Prompt URL")
    FUNCTION = "upload_to_r2"
    CATEGORY = "R2 Nodes"

    def upload_to_r2(self, image, prompt, negative_prompt, model, slack_webhook_url,
                     r2_access_key_id, r2_secret_access_key, r2_upload_path,
                     r2_endpoint, r2_bucket_name, r2_domain) -> Tuple[str, str]:
        try:
            # Validate image dimensions and format
            if not isinstance(image, dict) or "image" not in image:
                raise ValueError("Invalid image input format")

            img_array = image["image"]
            if len(img_array.shape) != 3 or img_array.shape[2] not in [3, 4]:
                raise ValueError("Image must be RGB or RGBA")

            if img_array.shape[0] < 32 or img_array.shape[1] < 32:
                raise ValueError("Image dimensions too small (minimum 32x32)")

            # Use environment variables as fallback for credentials
            r2_access_key_id = r2_access_key_id or os.getenv("R2_ACCESS_KEY_ID")
            r2_secret_access_key = r2_secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY")
            r2_endpoint = r2_endpoint or os.getenv("R2_ENDPOINT")
            r2_bucket_name = r2_bucket_name or os.getenv("R2_BUCKET_NAME")
            r2_domain = r2_domain or os.getenv("R2_DOMAIN")

            # Validate required R2 credentials
            if not all([r2_access_key_id, r2_secret_access_key, r2_endpoint, r2_bucket_name, r2_domain]):
                raise ValueError("Missing required R2 credentials in inputs or environment variables")

            # Save image to a temporary file
            temp_image_path = "temp_image.png"
            try:
                pil_image = Image.fromarray(image["image"])
                pil_image.save(temp_image_path)
                logger.info("Successfully saved temporary image")
            except Exception as e:
                logger.error(f"Failed to save temporary image: {str(e)}")
                raise

            # Generate SHA256 hash of the image file
            try:
                file_hash = self.generate_sha256_file(temp_image_path)
                logger.info(f"Generated file hash: {file_hash}")
            except Exception as e:
                logger.error(f"Failed to generate file hash: {str(e)}")
                raise

            # Create metadata dictionary
            data = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "model": model,
            }

            # Save metadata to JSON file
            output_json_path = f"{file_hash}.json"
            try:
                with open(output_json_path, 'w') as json_file:
                    json.dump(data, json_file, default=str)
                logger.info("Successfully saved metadata JSON")
            except Exception as e:
                logger.error(f"Failed to save metadata JSON: {str(e)}")
                raise

            # Upload JSON to R2
            try:
                prompt_url = self.upload_file_to_r2(
                    file_path=output_json_path,
                    file_name=f"{file_hash}.json",
                    r2_access_key_id=r2_access_key_id,
                    r2_secret_access_key=r2_secret_access_key,
                    r2_upload_path=r2_upload_path,
                    r2_endpoint=r2_endpoint,
                    r2_bucket_name=r2_bucket_name,
                    r2_domain=r2_domain
                )
                if not prompt_url:
                    raise Exception("Failed to get prompt URL from R2")
                logger.info(f"Successfully uploaded JSON to R2: {prompt_url}")
            except Exception as e:
                logger.error(f"Failed to upload JSON to R2: {str(e)}")
                raise

            # Upload image to R2
            try:
                img_url = self.upload_file_to_r2(
                    file_path=temp_image_path,
                    file_name=f"{file_hash}.png",
                    r2_access_key_id=r2_access_key_id,
                    r2_secret_access_key=r2_secret_access_key,
                    r2_upload_path=r2_upload_path,
                    r2_endpoint=r2_endpoint,
                    r2_bucket_name=r2_bucket_name,
                    r2_domain=r2_domain
                )
                if not img_url:
                    raise Exception("Failed to get image URL from R2")
                logger.info(f"Successfully uploaded image to R2: {img_url}")
            except Exception as e:
                logger.error(f"Failed to upload image to R2: {str(e)}")
                raise

            # Optionally send Slack message
            if slack_webhook_url:
                try:
                    payload = self.format_slack_message(
                        image_url=img_url,
                        prompt_url=prompt_url,
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        model=model
                    )
                    self.send_slack_message(payload, webhook_url=slack_webhook_url)
                    logger.info("Successfully sent Slack message")
                except Exception as e:
                    logger.error(f"Failed to send Slack message: {str(e)}")
                    # Don't raise here as Slack notification is optional

            return (img_url, prompt_url)

        except Exception as e:
            logger.error(f"Error in upload_to_r2: {str(e)}")
            raise
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                if os.path.exists(output_json_path):
                    os.remove(output_json_path)
                logger.info("Cleaned up temporary files")
            except Exception as e:
                logger.error(f"Failed to clean up temporary files: {str(e)}")

    def upload_file_to_r2(self, file_path, file_name, r2_access_key_id, r2_secret_access_key,
                          r2_upload_path, r2_endpoint, r2_bucket_name, r2_domain):
        try:
            r2 = R2Client(
                access_key=r2_access_key_id,
                secret_key=r2_secret_access_key,
                endpoint=r2_endpoint,
            )

            upload_path = f"{r2_upload_path}/{file_name}"
            r2.upload_file(r2_bucket_name, file_path, upload_path)
            url = f"https://{r2_domain}/{upload_path}"
            logger.info(f"Successfully uploaded file to R2: {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload file to R2: {str(e)}")
            return None

    def generate_sha256_file(self, file_path):
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as file:
                for byte_block in iter(lambda: file.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to generate SHA256 hash: {str(e)}")
            raise

    def format_slack_message(self, image_url, prompt_url, prompt, negative_prompt, model):
        blocks = {
            "blocks": [
                {
                    "type": "image",
                    "image_url": image_url,
                    "alt_text": "Generated Image"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🧠 Model:* {model}\n*📄 Prompt:* {prompt}\n*🚫 Negative Prompt:* {negative_prompt}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📷 Photo Link",
                                "emoji": True
                            },
                            "url": image_url
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📝 Prompt JSON",
                                "emoji": True
                            },
                            "url": prompt_url
                        }
                    ]
                }
            ]
        }
        return blocks

    def send_slack_message(self, payload, webhook_url):
        try:
            result = requests.post(webhook_url, json=payload)
            result.raise_for_status()
            logger.info("Successfully sent Slack message")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack message: {str(e)}")
            return None

# Register the node
NODE_CLASS_MAPPINGS.update({
    "R2BucketUploadNode": R2BucketUploadNode
})