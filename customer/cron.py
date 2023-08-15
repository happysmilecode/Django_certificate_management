from django_cron import CronJobBase, Schedule
from django.contrib.auth.models import User
from .models import Customer
from insurance import models as CMODEL
from fcm_django.models import FCMDevice
from datetime import datetime, timedelta

import logging

# Get the logger for the current module
logger = logging.getLogger(__name__)


class PushNotificationCronJob(CronJobBase):
    RUN_EVERY_MINS = 1  # every 2 hours

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'customer.my_cron_job'    # a unique code

    def do(self):
        devices = FCMDevice.objects.all()
        logger.info('This is an informational messages')
        for device in devices:
            user_id = device.user_id
            logger.info(f"User ID: {user_id}")
            customer_id = Customer.objects.values_list(
                'id', flat=True).get(user_id=user_id)
            expire_date = CMODEL.Category.objects.values_list(
                'expire_date', flat=True).get(customer_id=customer_id)
            logger.info(f"Expire_Date: {type(expire_date)}")
            if expire_date is None:
                print("expire_date is None")
            else:
                # Get current date and time
                current_date = datetime.now().date()

                # Calculate the date 3 months from now
                three_months_later = current_date + timedelta(weeks=12)

                if expire_date > three_months_later:
                    device.send_message(
                        title="Your Notification Title",
                        body="Your Notification Body"
                    )
                else:
                    print("expire_date is not more than 3 months later than today.")
