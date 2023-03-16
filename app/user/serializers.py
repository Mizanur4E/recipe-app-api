from django.contrib.auth import (
    get_user_model,
    authenticate,
)
from django.utils.translation import gettext as _

from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ['email', 'password', 'name']
        extra_kwargs = {'password': {'write_only': True, 'min_length': 5}}

    def create(self, validated_data):

        return get_user_model().objects.create_user(**validated_data)


class AuthTokenSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(
        style = {'input_type': 'password'},
        trim_whitespace = False,
    )

    def validate(self, attrs):

        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(
            request=self.context.get('request'),
            username= email,
            password=password,
        )

        if not user:
            msg = _('Unable to authenticate with provided credentials..!')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

    def test_create_token_blank_password(self):
        """Test posting a blank password returns an error."""
        payload = {'email': 'test@example.com', 'password': ''}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Test authentication is required for users."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)