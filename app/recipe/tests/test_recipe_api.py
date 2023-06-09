from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPE_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])



def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):

    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.24'),
        'description': 'Sample descriptionss ',
        'link': 'www.gmail.com',
    }

    defaults.update(params)

    recipe = Recipe.objects.create(user = user, **defaults)
    return recipe


class PublicRecipeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RECIPE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateRecipeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'tes@example.com',
            'test123'
        )
        self.client.force_authenticate(self.user)

    def test_retrive_recipes(self):

        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes,many= True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):

        other_user = get_user_model().objects.create_user(
            'other@ex.com',
            'pass454'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user= self.user)

        serializer = RecipeSerializer(recipes, many= True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):

        recipe = create_recipe(self.user)
        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):

        payload =  {
        'title': 'Sample recipe mine',
        'time_minutes': 19,
        'price': Decimal('10.24'),

    }

        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id= res.data['id'])

        for k,v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)


    def test_create_recipe_with_tags(self):

        payload = {
        'title': 'Thai recipe mine',
        'time_minutes': 21,
        'price': Decimal('1.24'),
        'tags': [{'name': 'thai'}, {'name': 'lunch'}]
        }

        res = self.client.post(RECIPE_URL, payload, format= 'json')


        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user= self.user)

        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]

        self.assertEqual(recipe.tags.count(), 2)

        for tag in payload['tags']:

            exists = recipe.tags.filter(
                name = tag['name'],
                user = self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):

        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'lunch'}]}
        url = detail_url(recipe.id)

        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user= self.user, name='lunch')
        self.assertIn(new_tag, recipe.tags.all())


    def test_updates_recipe_assign_tag(self):

        tag_breakfast = Tag.objects.create(user= self.user, name= 'Breakfast')
        recipe = create_recipe(user= self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user= self.user, name='lunch')
        payload = {'tags': [{'name':'lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):

        tag_breakfast = Tag.objects.create(user= self.user, name= 'Breakfast')
        recipe = create_recipe(user= self.user)

        recipe.tags.add(tag_breakfast)


        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)


    def test_filter_by_tags(self):

        r1 = create_recipe(user=self.user, title='recipe1')
        r2 = create_recipe(user=self.user, title='recipe2')

        tag1 = Tag.objects.create(user=self.user, name='tag11')
        tag2 = Tag.objects.create(user=self.user, name='tag21')

        r1.tags.add(tag1)
        r2.tags.add(tag2)

        r3 = create_recipe(user=self.user, title= 'recipe345 me')

        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)




class ImageUploadTests(TestCase):


    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'tes@example.com',
            'test123'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)


    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):

        url = image_upload_url(self.recipe.id)

        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:

            img = Image.new('RGB', (10, 10))
            img.save(image_file)
            image_file.seek(0)
            payload = {'image': image_file}

            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))


    def test_upload_image_bad_request(self):

        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format= 'multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)