
from django_mongodb_cascade import cascade_embedded


class cascade_embedded_list(cascade_embedded):
    """Cascade saves and deletes to related models where the embedded object
        is stored in a list

    See 'cascade_embedded' class for description of arguments/options
    """
    def _set_embedded_attribute(self, obj, field_name, instance, delete=False):
        """Find the 'instance' inside the obj.field_name and update it."""
        obj = self._get_nested_field_obj(obj, field_name)
        field = getattr(obj, field_name[-1])
        # Iterate over the field and find the instance.
        for item in field:
            if item.pk == instance.pk:
                # If the field is a list, then we want to record the index
                # and replace it there to maintain order
                if isinstance(field, list):
                    index = field.index(item)
                    field.remove(item)
                    # If the model was deleted, then we just remove
                    if not delete:
                        field.insert(index, instance)

                # If the field is a set, then order doesn't matter so we just
                # stick it in.
                elif isinstance(field, set):
                    field.remove(item)
                    if not delete:
                        field.add(instance)
                else:
                    raise TypeError("Unable to update the embedded instance "
                                    "inside type: '%s'" % type(field).__name__)
