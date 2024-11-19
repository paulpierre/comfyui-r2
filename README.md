# 🌩️ comfyui-r2

<div align="center">
A portal gun for your ComfyUI generated images

<img src="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExcDBzZGF2azBnZ2F0YzJqbzBodWc5enZhaDM1YmFqZnQ1cnZmOG9mZCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3oriNTivEJZ1ASRnMc/giphy.gif" width="300" /></div>

Wish your instance of ComfyUI had automatic asset management and sharing?

You've found the right repo. comfyui-r2 is a custom node that automatically uploads generated images and workflow configuration metadata as JSON to Cloudflare's R2 bucket storage. As a bonus, it also provides an optional feature to post the uploaded data to a custom Slack webhook for easy sharing and collaboration.

## 🚀 Features

- 📷 Uploads generated images to Cloudflare R2 storage
- 📝 Uploads JSON workflow metadata alongside the images
- 🔒 Securely stores and retrieves images and metadata
- 💬 Optionally posts the uploaded data to a Slack webhook for sharing
- 🔗 Shares image and workflow JSON link with image preview in Slack

## 🛠️ Installation

1. Clone this repository into your ComfyUI custom_nodes folder:

    ```bash
    cd ComfyUI/custom_nodes/
    git clone https://github.com/paulpierre/comfyui-r2
    ```

2. Install the required dependencies:
    ```bash
    cd comfyui-r2
    pip install -r requirements.txt
    ```

3. Restart ComfyUI and you should see the R2 Upload node in your nodes list
    [Screenshot placeholder: Show R2 Upload node in node list]

4. Configure your R2 settings in the node:
    [Screenshot placeholder: Show R2 Upload node settings]

    All the fields are required, for r2 domain you can just keep the default root domain if you don't have a custom domain setup.

    - **R2 Access Key ID**: Your Cloudflare R2 access key ID
    - **R2 Secret Access Key**: Your Cloudflare R2 secret access key
    - **R2 Upload Path**: The desired upload path within your R2 bucket (default: "assets")
    - **R2 Endpoint**: The endpoint URL for your R2 bucket
    - **R2 Bucket Name**: The name of your R2 bucket
    - **R2 Domain**: The domain associated with your R2 bucket
    - **Slack Webhook URL (optional)**: The URL of your Slack webhook for posting the uploaded data

5. If you haven't already set up Cloudflare R2, [create one for free](https://developers.cloudflare.com/r2/)

6. Optionally configure Slack integration via [Incoming Webhooks](https://api.slack.com/messaging/webhooks). Below you can see what it would look like:
    [Screenshot placeholder: Show Slack message with image and metadata]

    - Workflow name and node configuration are displayed
    - Image URL and image preview are provided
    - Link to the workflow JSON is provided

## ⚙️ Environment variables
Environment variables are supported

```bash
# Example .env or environment variable export setup
R2_BUCKET_NAME=production-bucket
R2_UPLOAD_PATH=assets
R2_DOMAIN=example.com
R2_ACCESS_KEY_ID=e2a2cf725d0c49d887b9b0a815c4cb56
R2_SECRET_ACCESS_KEY=2565b9d469be4b549e426f1feb08c952
R2_ENDPOINT=https://r2.cloudflare.com/1/production-bucket
```

## 🖼️ Usage
1. Add the R2 Upload node to your workflow
2. Connect your image output to the R2 Upload node
3. Configure your R2 credentials in the node settings
4. Run your workflow as usual

The node will automatically upload the generated image and its corresponding workflow JSON to your specified R2 bucket.

If a Slack webhook URL is provided, the node will also post the uploaded data to the specified Slack channel.
The generated shareable links will be displayed in the node's output.

### 📄 JSON Metadata Format
The JSON metadata file contains your workflow configuration:
```json
{
   "workflow_name": "My Amazing Workflow",
   "node_id": "12345",
   "timestamp": "2024-03-20T10:30:00Z",
   "configuration": {
     "model": "sdxl_1.0",
     "prompt": "a beautiful sunset over the ocean",
     "negative_prompt": "blur, darkness",
     "steps": 20,
     "cfg_scale": 7,
     "seed": 12345678
   },
   ... etc.
}
```

## 📜 License
This custom node is released under the MIT License.

Enjoy. PRs welcome and happy generating! 🎉