#django_mongodb_cascade
======================

Cascade saves and deletes to models that are embedding the saved/deleted model instance. This is meant for django-nonrel, and it may only work with Merchant Atlas' edited version of [mongodb-engine](https://github.com/MerchantAtlas/mongodb-engine) (I haven't used this with the original). 


Typically, when one model is embedded in another, it will not be updated if the instance of the embedded model is changed. This class decorator incorporates `post_init`, `post_save` and `post_delete` signals into the decorated model to ensure changes to its instances are reflected in the models that are embedding them. 

Since this library uses django signals to manage the embedded-model updates, circumventing the normal Django saving process will render this ineffective. 

####Example:
```python
class Organization(models.Model):
    user_profile = djangotoolbox.fields.EmbeddedModelField("account.UserProfile")


@cascade_embedded("account.Organization", "user_profile")
class UserProfile(models.Model)
    name = models.CharField(max_length=255)

# Update a user profile from an organization
org = Organization.objects.all()[0]
up = org.user_profile
print up.name
George

up.name = "Bob"
up.save()

# Requery the organization to see the changes in the embedded model.
org = Organization.objects.get(id=org.id)
print org.up.name
Bob
```

###Required Arguments:

#####target_model:
The model that is embedding this model, and that will be updated with the changes to this model's instances. E.g. `"account.Organization"` above. 
#####field_name: 
The name of the field that will contain the embedded instance in the target model. E.g. `"user_profile"` above. 

Note: Dot-notation is supported, so something like `"user_profile.city"` will work.

####Options:
#####pre_save_function: 
A function to execute before each embedded instance is saved in the target model

#####post_save_function: 
A function to execute after each embedded instance is saved in the target model. This is attempted regardless of any exceptions that are raised during saving.

#####override_save_function: 
This library creates a function that runs during a "Post Save" Django signal. The user can override that by providing a function here. The user can also provide the value `None`. In that case, no post_save signal will be attached at all.

#####pre_delete_function:  
A function to execute before each embedded instance is deleted from the target model 

#####post_delete_function: 
A function to execute after each embedded instance is deleted in the target model. This is attempted regardless of any exceptions that are raised during saving.

#####override_delete_function: 
This library creates a function that runs during a "Post Delete" Django signal. The user can override that by providing a function here. The user can also provide the value `None`. In that case, no post_delete signal will be attached at all.

#####watch_fields: 
A list of fields in the embedded model to watch for changes. If this field is defined, the target model will only be updated when one of the listed fields are changed. This only applies to saving, since deletion deletes the whole instance.
