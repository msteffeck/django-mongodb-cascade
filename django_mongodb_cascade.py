
from django.db import models
from django.db.models import signals
from django_mongodb_engine.query import A


def get_model(cls, model_str):
    if isinstance(model_str, basestring):
        # Get the "app.Model" from the model string
        try:
            app_label, model_name = model_str.split(".")
        except ValueError:
            # If we can't split, assume the model is in the current app
            app_label = cls._meta.app_label
            model_name = model_str
        model_cls = models.get_model(app_label, model_name)
    elif isinstance(model_str, models.Model):
        model_cls = model_str
    else:
        raise TypeError("'model' must be either a model class or a "
                        "string model relation.")
    return model_cls


def build_save_signal_function(cls, field_name, model_str,
                               pre_save_function, post_save_function):
    """Build the function called by the post_save signal

    This will update the given field in the given model with the
    saved data.
    """
    def save_signal_function(sender, instance, created, *args, **kwargs):
        model_cls = get_model(cls, model_str)
        # If this is a newly created model, there won't be an embedded
        # field that needs to be updated
        if created:
            return

        if pre_save_function:
            pre_save_function(sender, instance, created, *args, **kwargs)

        # Can't use 'update()' on embedded models. It would be better
        # to do that instead of iterating and saving individually.
        filter_args = {field_name: A('id', instance.id)}
        for obj in model_cls.objects.filter(**filter_args):
            setattr(obj, field_name, instance)
            obj.save()

        if post_save_function:
            post_save_function(sender, instance, created, *args, **kwargs)
    return save_signal_function


def build_delete_signal_function(cls, field_name, model_str,
                                 pre_delete_function, post_delete_function):
    """Build the function called by the post_delete signal

    This will set the given field in the given model to 'None'
    """
    def delete_signal_function(sender, instance, *args, **kwargs):
        model_cls = get_model(cls, model_str)

        if pre_delete_function:
            pre_delete_function(sender, instance, *args, **kwargs)

        # Can't use 'update()' on embedded models. It would be better
        # to do that instead of iterating and saving individually.
        filter_args = {field_name: A('id', instance.id)}
        for obj in model_cls.objects.filter(**filter_args):
            setattr(obj, field_name, None)
            obj.save()

        if post_delete_function:
            post_delete_function(sender, instance, *args, **kwargs)
    return delete_signal_function


def cascade_embedded(model, field_name, pre_save_function=None,
                     post_save_function=None, override_save_function=None,
                     pre_delete_function=None, post_delete_function=None,
                     override_delete_function=None):
    """Cascade saves and deletes to related models.

    When one model is embedded in another, it will not be updated if the
    instance of the embedded model is changed. This class decorator
    incorporates post_save and post_delete signals into the decorated model.

    Example:
    >>>@cascade_embedded("account.Organization", "user_profile")
    >>>class UserProfile(models.Model)
    """
    def wrapper(cls):
        # Prepare the post_save signal
        if override_save_function:
            save_signal_function = override_save_function
        else:
            save_signal_function = build_save_signal_function(
                                        cls, field_name, model,
                                        pre_save_function, post_save_function)

        # Prepare the post_delete signal
        if override_delete_function:
            delete_signal_function = override_delete_function
        else:
            delete_signal_function = build_delete_signal_function(
                                    cls, field_name, model,
                                    pre_delete_function, post_delete_function)

        # Weak=False because the functions will be garbage collected otherwise
        if save_signal_function:
            signals.post_save.connect(save_signal_function,
                                      sender=cls, weak=False)
        if delete_signal_function:
            signals.post_delete.connect(delete_signal_function,
                                        sender=cls, weak=False)
        return cls
    return wrapper

