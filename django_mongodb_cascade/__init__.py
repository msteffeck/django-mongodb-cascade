from collections import Hashable


WATCH_FIELDS_HASH_ATTRIBUTE = "_dmc_watch_fields_hash"


def deep_hash(value):
    """Iterate over a value and recurse to build a serviceable hash.

    If the value is a simple hashable value, it will be hashed and returned.
    If the value is a (standard) non-hashable object, this function will
    attempt to build a hash.

    Note: Any objects that want a more sophisticated hashing done to them
          should override the __hash__() method
    """
    if isinstance(value, Hashable):
        return hash(value)
    else:
        if isinstance(value, dict):
            return hash(tuple((k, deep_hash(v)) for k, v in value.iteritems()))
        elif isinstance(value, (list, set, tuple)):
            return hash(tuple(deep_hash(v) for v in value))
        else:
            raise TypeError("Unhashable type: '%s'" % type(value).__name__)


from cascade_embedded import cascade_embedded
from cascade_embedded_list import cascade_embedded_list
