import launch
if not launch.is_installed("r2client"):
    launch.run_pip("install r2client==0.2.1", "r2client: requirements for Cloudflare R2")
if not launch.is_installed("requests"):
    launch.run_pip("install requests", "requests: requirements for Cloudflare R2")
