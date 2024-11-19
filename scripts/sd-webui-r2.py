from modules import scripts, shared, script_callbacks
from r2client.R2Client import R2Client
from modules.shared import opts
from typing import Optional
import requests
import logging
import hashlib
import json
import os


print("🔥 [R2BucketUpload] Loaded")

# Add options for R2 configuration
def on_ui_settings():
    section = ("r2", "R2 Settings")
    shared.opts.add_option("r2_access_key_id", shared.OptionInfo("", "R2 Access Key ID", section=section))
    shared.opts.add_option("r2_secret_access_key", shared.OptionInfo("", "R2 Secret Access Key", section=section))
    shared.opts.add_option("r2_upload_path", shared.OptionInfo("assets", "R2 Upload Path", section=section))
    shared.opts.add_option("local_upload_path", shared.OptionInfo("output", "Local Upload Path", section=section))
    shared.opts.add_option("r2_endpoint", shared.OptionInfo("", "R2 Endpoint", section=section))
    shared.opts.add_option("r2_bucket_name", shared.OptionInfo("", "R2 Bucket Name", section=section))
    shared.opts.add_option("r2_domain", shared.OptionInfo("", "R2 Domain", section=section))
    shared.opts.add_option("slack_webhook_url", shared.OptionInfo("", "Slack Webhook URL", section=section))

script_callbacks.on_ui_settings(on_ui_settings)

class R2BucketUpload(scripts.Script):

    def title(self):
        return "R2 Bucket upload"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

def postprocess(params:script_callbacks.ImageSaveParams, *args):

    print("⚡ [R2BucketUpload] Starting post processing ..")

    slack_webhook_url = opts.slack_webhook_url

    p = params.p

    data = p.__dict__

    print(f"⚡ [R2BucketUpload] JSON data: {data}")

    output_file_path = params.filename  # Path to the output image
    file_hash = generate_sha256_file(output_file_path)
    output_json_path = os.path.join(os.path.dirname(output_file_path), f"{file_hash}.json")

    with open(output_json_path, 'w') as json_file:
        json.dump(data, json_file, default=str)

    print(f"🔄 [R2BucketUpload] Uploading json {output_json_path} to R2")
    prompt_url = upload_to_r2(output_json_path)

    # Clean up
    os.remove(output_json_path)

    img_url = ""

    print(f"🔄 [R2BucketUpload] Uploading image {output_file_path} to R2")
    img_url = upload_to_r2(output_file_path, file_name=f"{file_hash}.png")

    if slack_webhook_url:
        print("🚀 Sending slack message")
        payload = format_slack_message(
            img_url,
            prompt_url,
            data.get('prompt'),
            data.get('negative_prompt'),
            data.get('sd_model_name')
        )
        send_slack_message(payload, webhook_url=slack_webhook_url)

    print("✅ [R2BucketUpload] Successfully uploaded to R2")


def upload_to_r2(file_path, file_name: Optional[str] = None):
    file_name = file_name or os.path.basename(file_path)

    bucket_name = opts.r2_bucket_name or os.getenv("R2_BUCKET_NAME")
    base_upload_path = opts.r2_upload_path or os.getenv("R2_UPLOAD_PATH")
    bucket_domain = opts.r2_domain or os.getenv("R2_DOMAIN")
    access_key_id = opts.r2_access_key_id or os.getenv("R2_ACCESS_KEY_ID")
    secret_access_key = opts.r2_secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY")
    bucket_endpoint = opts.r2_endpoint or os.getenv("R2_ENDPOINT")

    r2 = R2Client(
        access_key=access_key_id,
        secret_key=secret_access_key,
        endpoint=bucket_endpoint,
    )

    upload_path = f"{base_upload_path}/{file_name}"
    print(f"🔄 [R2BucketUpload] Uploading file to R2 - bucket_name:{bucket_name} file_path:{file_path} upload_path:{upload_path}")
    try:
        r2.upload_file(bucket_name, file_path, upload_path)
    except Exception as e:
        print(f"❌ [R2BucketUpload] Failed to upload file to R2: {e}")
        return None

    url = f"https://{bucket_domain}/{upload_path}"

    return url

def generate_sha256_file(file_path):
    """
    Generate a SHA256 hash of a file.

    :param file_path: Path to the file to hash
    :return: SHA256 hash of the file
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def format_slack_message(
    image_url: str,
    prompt_url: str,
    prompt: str,
    negative_prompt: str,
    model: str
) -> dict:

    blocks ={
	"blocks": [
        {
            "type": "image",
            "image_url": image_url,
            "alt_text": "delicious tacos"
        },
		{
			"type": "rich_text",
			"elements": [
				{
					"type": "rich_text_section",
					"elements": [
						{
							"type": "text",
							"text": f"🧠 Model: {model}"
						},
						{
							"type": "text",
							"text": f"\n📄 Prompt: {prompt}"
						},
						{
							"type": "text",
							"text": f"\n🚫 Negative Prompt: {negative_prompt}\n"
						}
					]
				},

				{
					"type": "rich_text_section",
					"elements": [
						{
							"type": "link",
							"url": image_url,
							"text": "\n📷 Photo link ",
							"style": {
								"bold": True
							}
						},
						{
							"type": "link",
							"url": prompt_url,
							"text": "📝 Prompt JSON ",
							"style": {
								"bold": True
							}
						}
					]
				}
			]
		}
	]
}
    return blocks


def send_slack_message(payload: dict, webhook_url: Optional[str] = None):
    webhook_url = webhook_url or opts.slack_webhook_url or os.environ["SLACK_WEBHOOK_URL"]
    if webhook_url is None:
        raise ValueError("Webhook URL is required to send a Slack message.")

    # Send Slack notification
    result = requests.post(webhook_url, json=payload)
    print(f"💬 [R2BucketUpload] Slack response: {result.text}")
    return result

script_callbacks.on_image_saved(postprocess)
