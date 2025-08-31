INSTALLED_APPS = [
    "django_crontab",
    "django_celery_beat"
]

# All cron jobs in one list
CRONJOBS = [
    # A) Customer cleanup — Sundays 02:00
    ("0 2 * * 0", "crm.cron.customer_cleanup"),

    # B) Order reminders — Daily 08:00
    ("0 8 * * *", "crm.cron.send_order_reminders"),

    # C) Heartbeat — Every 5 minutes
    ("*/5 * * * *", "crm.cron.log_crm_heartbeat"),

    # D) Low stock updater — Every 12 hours
    ("0 */12 * * *", "crm.cron.update_low_stock"),
]
