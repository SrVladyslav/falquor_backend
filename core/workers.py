from core.celery import worker as default_worker
from core.celery_email_broker import email_worker


def worker(queue="default"):
    """
    Custom decorator to register tasks in Celery with the correct queue.

    This decorator allows you to specify which queue (either "default" or "emails") the task should be assigned to.

    Args:
        queue (str): The name of the queue to assign the task to.
                     Valid options are "default" or "emails". Default is "default".

    Returns:
        function: A decorator that registers the task in Celery with the appropriate worker for the specified queue.

    Raises:
        ValueError: If an invalid queue name is provided (not "default" or "emails").
    """

    # Selecting the appropriate worker based on the queue name
    if queue == "default":
        app = default_worker
    elif queue == "emails":
        app = email_worker
    else:
        raise ValueError(f"Unknown queue name: {queue}. Must be 'default' or 'emails'.")

    # def decorator(task_func):
    #     # Wrapper function that simply calls the original task function
    #     def wrapper(*args, **kwargs):
    #         return task_func(*args, **kwargs)

    #     # Apply the Celery task decorator to the wrapper, associating it with the specified queue
    #     wrapper = app.task(queue=queue)(wrapper)

    #     # Return the wrapped function, which is now a Celery task
    #     return wrapper
    def decorator(task_func):
        return app.task(queue=queue)(task_func)

    return decorator
