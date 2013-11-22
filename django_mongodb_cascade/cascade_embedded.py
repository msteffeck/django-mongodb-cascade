import hashlib

from django.db import models
from django.db.models import signals
from django_mongodb_engine.query import A

from django_mongodb_cascade import WATCH_FIELDS_HASH_ATTRIBUTE, deep_hash


class cascade_embedded(object):
    """Cascade saves and deletes to related models.

    When one model is embedded in another, it will not be updated if the
    instance of the embedded model is changed. This class decorator
    incorporates post_save and post_delete signals into the decorated model.

    Example:
    >>>@cascade_embedded("account.Organization", "user_profile")
    >>>class UserProfile(models.Model)

    Required Arguments:
    :param target_model: The model that is embedding this model, and
            that will be updated with the changes to this model's instances.
    :param field_name: The name of the field that will contain the embedded
            instance in the target model.

    Options:
    :param pre_save_function: A function to execute before each embedded
            instance is saved in the target model
    :param post_save_function: A function to execute after each embedded
            instance is saved in the target model. This is attempted
            regardless of any exceptions that are raised during saving.
    :param override_save_function: This library creates a function that runs
            during a "Post Save" Django signal. The user can override that
            by providing a function here.
            The user can also provide the value "None". In that case, no
            post_save signal will be attached at all.

    :param pre_delete_function:  A function to execute before each embedded
            instance is deleted from the target model
    :param post_delete_function: A function to execute after each embedded
            instance is deleted in the target model. This is attempted
            regardless of any exceptions that are raised during saving.
    :param override_delete_function: This library creates a function that runs
            during a "Post Delete" Django signal. The user can override that
            by providing a function here.
            The user can also provide the value "None". In that case, no
            post_delete signal will be attached at all.

    # TODO: Add support
    :param watch_fields: A list of fields in the embedded model to watch
            for changes. If this field is defined, the target model will only
            be updated when one of the listed fields are changed. This only
            applies to saving, since deletion deletes the whole instance.
    """
    def __init__(self, target_model, field_name, **kwargs):
        self.target_model = target_model
        self.field_name = field_name
        self.options = kwargs

    def __call__(self, cls):
        watch_fields = self.options.get('watch_fields')

        # Prepare the post_save signal
        override_save_function = self.options.get('override_save_function', -1)
        if override_save_function != -1:
            save_signal_function = override_save_function
        else:
            save_signal_function = self.build_save_signal_function(
                                        cls, self.field_name,
                                        self.target_model, watch_fields,
                                        self.options.get('pre_save_function'),
                                        self.options.get('post_save_function'))

        # Prepare the post_delete signal
        override_delete_function = self.options.get('override_delete_function',
                                                    -1)
        if override_delete_function != -1:
            delete_signal_function = override_delete_function
        else:
            delete_signal_function = self.build_delete_signal_function(
                                    cls, self.field_name, self.target_model,
                                    self.options.get('pre_delete_function'),
                                    self.options.get('post_delete_function'))

        # weak=False because the functions will be garbage collected otherwise
        if save_signal_function:
            signals.post_save.connect(save_signal_function,
                                      sender=cls, weak=False)
        if delete_signal_function:
            signals.post_delete.connect(delete_signal_function,
                                        sender=cls, weak=False)

        if watch_fields:
            init_signal_function = self.build_init_signal_function(
                                        watch_fields)
            signals.post_init.connect(init_signal_function,
                                      sender=cls, weak=False)
        return cls

    def get_model(self, cls, model_str):
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

    def _build_watch_fields_hash(self, instance, watch_fields):
        """Build the hash for the watch fields"""
        # Build a hash of all of the 'watch_fields'. If the hash changes
        # then we'll know the embedded instance needs to be updated.
        values = [str(deep_hash(getattr(instance, field_name, None)))
                  for field_name in watch_fields]

        # Now combine all of the field hashes into an md5 hash.
        md5 = hashlib.md5()
        md5.update("".join(values))
        return md5.hexdigest()

    def build_init_signal_function(self, watch_fields):
        """Build the post_init signal function.

        This generates a hash of the model values immediately after the init
        finishes, so we can keep track of what changes.
        """
        def init_signal_function(sender, instance, *args, **kwargs):
            watch_fields_hash = self._build_watch_fields_hash(instance,
                                                              watch_fields)
            setattr(instance, WATCH_FIELDS_HASH_ATTRIBUTE, watch_fields_hash)
        return init_signal_function

    def build_save_signal_function(self, cls, field_name,
                                   model_str, watch_fields,
                                   pre_save_function, post_save_function):
        """Build the function called by the post_save signal

        This will update the given field in the given model with the
        saved data.
        """
        def save_signal_function(sender, instance, created, *args, **kwargs):
            model_cls = self.get_model(cls, model_str)
            # If this is a newly created model, there won't be an embedded
            # field that needs to be updated
            if created:
                return

            # If the watch_fields are defined, we'll check their values with
            # a hash. If the hash is the same, then none of them were changed.
            if watch_fields:
                watch_fields_hash = self._build_watch_fields_hash(instance,
                                                                  watch_fields)
                if watch_fields_hash == getattr(instance,
                                                WATCH_FIELDS_HASH_ATTRIBUTE,
                                                None):
                    return
                # If the hashes don't match, that means we will need to update.
                # In that case, we need to save the new hash.
                else:
                    setattr(instance, WATCH_FIELDS_HASH_ATTRIBUTE,
                            watch_fields_hash)

            # Can't use 'update()' on embedded models. Besides, we need to be
            # able to run the pre and post save functions
            filter_args = self._get_filter_args(field_name, instance)
            for obj in model_cls.objects.filter(**filter_args):
                if pre_save_function:
                    pre_save_function(sender, instance, created,
                                      embedded_instance=obj,
                                      *args, **kwargs)
                try:
                    self._set_embedded_attribute(obj, field_name, instance)
                    obj.save()
                finally:
                    if post_save_function:
                        post_save_function(sender, instance, created,
                                           embedded_instance=obj,
                                           *args, **kwargs)
        return save_signal_function

    def build_delete_signal_function(self, cls, field_name, model_str,
                                    pre_delete_function, post_delete_function):
        """Build the function called by the post_delete signal

        This will set the given field in the given model to 'None'
        """
        def delete_signal_function(sender, instance, *args, **kwargs):
            model_cls = self.get_model(cls, model_str)

            # Can't use 'update()' on embedded models. Besides, we need to be
            # able to run the pre and post delete functions
            filter_args = self._get_filter_args(field_name, instance)
            for obj in model_cls.objects.filter(**filter_args):
                if pre_delete_function:
                    pre_delete_function(sender, instance,
                                        embedded_instance=obj,
                                        *args, **kwargs)
                try:
                    self._set_embedded_attribute(obj, field_name, instance,
                                                 delete=True)
                    obj.save()
                finally:
                    if post_delete_function:
                        post_delete_function(sender, instance,
                                             embedded_instance=obj,
                                             *args, **kwargs)
        return delete_signal_function

    def _get_filter_args(self, field_name, instance):
        return  {field_name: A('id', instance.id)}

    def _set_embedded_attribute(self, obj, field_name, instance, delete=False):
        if delete:
            setattr(obj, field_name, None)
        else:
            setattr(obj, field_name, instance)


