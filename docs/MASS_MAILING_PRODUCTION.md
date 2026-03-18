# Production Guide: Mass Mailing & Background Tasks

In a local development environment, the Mass Mailing app uses Python's built-in `threading` module to sleep and wait until the scheduled time to send emails. This is great for testing without requiring complex infrastructure.

However, **in a Production Environment**, relying solely on background threads spawned from web requests is generally discouraged. 

## Why you need a Cronjob in Production

1. **Web Server Timeouts/Restarts**: Production web servers (like Gunicorn, uWSGI, or Apache) routinely kill and restart worker processes to manage memory. If your server restarts while a thread is "sleeping" and waiting to send an email, that thread will be killed, and the email will never be sent.
2. **Reliability**: A cronjob is managed by the operating system. It guarantees that the `process_mail_queue` command will run at the exact intervals you specify, regardless of what the web server is doing.
3. **Resilience**: If a campaign crashes midway through sending, the thread approach dies permanently. A cronjob will simply wake up a minute later, see the unfinished campaign, and pick up exactly where it left off.

## Recommended Production Setup

When you deploy this code to your production server (e.g., an Ubuntu/Linux VPS), you should configure a Cronjob to run the `process_mail_queue` command every minute.

### 1. Edit the Crontab
Log into your production server and edit the crontab for the user that runs your Django application (often `ubuntu`, `www-data`, or your personal user):

```bash
crontab -e
```

### 2. Add the Cron Expression
Depending on your server's resources and how frequently your team sends mass emails, you should choose an appropriate interval.

**Option A: Every 5 Minutes (Recommended for Resource Efficiency)**
This is the best balance. It checks the queue every 5 minutes. It uses very little CPU/RAM, and a 5-minute delay on a "scheduled" marketing email is perfectly acceptable.

```text
*/5 * * * * cd /path/to/your/mi_crm && /path/to/your/venv/bin/python manage.py process_mail_queue >> /path/to/your/mi_crm/logs/mail_queue.log 2>&1
```

**Option B: Every 1 Minute (For High-Volume/Immediate Needs)**
If you need emails to go out the *exact* minute they are scheduled, use this. The script is designed to be lightweight and will immediately exit if there are no emails to send, so it won't crash your server, but it does cause a tiny CPU spike every 60 seconds.

```text
* * * * * cd /path/to/your/mi_crm && /path/to/your/venv/bin/python manage.py process_mail_queue >> /path/to/your/mi_crm/logs/mail_queue.log 2>&1
```

**Make sure to replace the paths with your actual production paths:**
* `/path/to/your/mi_crm` -> The directory where your `manage.py` lives.
* `/path/to/your/venv/bin/python` -> The absolute path to the Python executable inside your virtual environment.

### How it works alongside the code:
The code in `mass_mailing/views.py` still spawns a background thread. This is actually a good thing! It means:
* **Immediate Sends**: If a user clicks "Send Now", the thread will trigger the queue immediately without having to wait up to 60 seconds for the next cron tick.
* **Scheduled Sends**: The thread will attempt to sleep and send it. If the thread survives, it sends the email. If the server restarts and kills the thread, your **Cronjob** acts as the ultimate safety net, ensuring the scheduled emails still go out on time.

This hybrid approach gives you the best of both worlds: immediate responsiveness and rock-solid production reliability.