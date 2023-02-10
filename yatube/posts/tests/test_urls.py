from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from posts.models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(
            username='Авторизованный пользователь'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
        )
        cls.public_url_address = {
            'posts/index.html': '',
            'posts/group_list.html': f'/group/{cls.group.slug}/',
            'posts/profile.html': f'/profile/{cls.author.username}/',
            'posts/post_detail.html': f'/posts/{cls.post.id}/',
        }

        cls.private_url_address = {
            '/create/': 'posts/create_post.html',
            f'/posts/{cls.post.id}/edit/': 'posts/create_post.html',
        }

        cls.templates_url_address = {
            '': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.author.username}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{cls.post.id}/edit/': 'posts/create_post.html',
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_public_url_exists_at_desired_location(self):
        """Страница address доступна любому пользователю."""

        for template, address in self.public_url_address.items():
            with self.subTest(template=template):
                response = self.client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_url_exists_at_desired_location_authorized(self):
        """Страница adress доступна авторизованному пользователю."""

        for address, template in self.private_url_address.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_url_redirect_anonymous_on_admin_login(self):
        """Страница adress перенаправит анонимного
        пользователя на страницу логина.
        """

        for address, template in self.private_url_address.items():
            with self.subTest(template=template):
                response = self.client.get(address, follow=True)
                self.assertRedirects(
                    response, f'/auth/login/?next={address}'
                )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""

        for address, template in self.templates_url_address.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
