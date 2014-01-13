from setuptools import setup

setup(
    name='django-mongodb-cascade',
    version='0.1.0',
    author='Michael Steffeck/Merchant Atlas Inc.',
    author_email="msteffeck@merchantatlas.com",
    url='https://github.com/MerchantAtlas/django-mongodb-cascade',
    license='3-clause BSD',
    description="Cascade saves and deletes to models that are embedding the "
                "saved/deleted model instance",
    packages=("django_mongodb_cascade",),
)
