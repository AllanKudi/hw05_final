from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django import forms

from ..models import Group, Post, Follow
from ..views import LIMIT_POSTS_ON_THE_PAGE

User = get_user_model()
NUMBER_POSTS_FOR_TEST_PAGINATOR = 13


class PostPagesTests(TestCase):
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
            group=cls.group,
        )

        cls.templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': cls.group.slug}
                    ): 'posts/group_list.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': cls.post.id}
                    ): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': cls.post.id}
                    ): 'posts/create_post.html',
            reverse('posts:profile',
                    kwargs={'username': cls.author.username}
                    ): 'posts/profile.html',
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""

        for reverse_name, template in self.templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_home_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author.username
        post_id_0 = first_object.id
        post_group_0 = first_object.group.id
        post_image_0 = first_object.image
        self.assertEqual(post_image_0, self.post.image)
        self.assertEqual(post_group_0, self.group.id)
        self.assertEqual(post_id_0, self.post.id)
        self.assertEqual(post_text_0, self.post.text)
        self.assertEqual(post_author_0, self.author.username)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context.get('group').title,
                         self.group.title)
        self.assertEqual(response.context.get('group').description,
                         self.group.description)
        self.assertEqual(response.context.get('group').slug, self.group.slug)
        self.assertEqual(response.context.get('group').id, self.group.id)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.author.username})
        )
        self.assertEqual(response.context.get('author').username,
                         self.author.username)
        self.assertEqual(response.context.get('author').id,
                         self.author.id)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse(
                    'posts:post_detail', kwargs={'post_id': self.post.id})))
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author.username,
                         self.author.username)
        self.assertEqual(response.context.get('post').id, self.post.id)
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_correct_cache_for_index_page(self):
        """Кэш главной страницы хранит посты пока не будет очищен."""
        response = self.authorized_client.get(reverse('posts:index'))
        post_count_before_del = response.content
        Post.objects.all().delete()
        response2 = self.authorized_client.get(reverse('posts:index'))
        post_count_after_del = response2.content
        self.assertEqual(len(post_count_before_del), len(post_count_after_del))
        cache.clear()
        response3 = self.authorized_client.get(reverse('posts:index'))
        post_count_after_clear = response3.content
        self.assertNotEqual(
            len(post_count_after_del),
            len(post_count_after_clear)
        )


class PaginatorViewsTest(TestCase):
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
        for post_number in range(NUMBER_POSTS_FOR_TEST_PAGINATOR):
            cls.post = Post.objects.create(
                author=cls.author,
                text='Тестовый пост',
                group=cls.group,
            )
        cls.namespaces = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.author.username}),
        ]

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_first_page_contains_ten_records(self):
        for reverse_name in self.namespaces:
            response = self.client.get(reverse_name)
            count_posts = len(response.context['page_obj'])
            self.assertEqual(count_posts,
                             LIMIT_POSTS_ON_THE_PAGE)

    def test_second_page_contains_three_records(self):
        for reverse_name in self.namespaces:
            response = self.client.get(reverse_name + '?page=2')
            count_second_page = (NUMBER_POSTS_FOR_TEST_PAGINATOR
                                 - LIMIT_POSTS_ON_THE_PAGE)
            self.assertEqual(len(response.context['page_obj']),
                             count_second_page)


class FollowTests(TestCase):
    def setUp(self):
        self.client_following = Client()
        self.client_follower = Client()
        self.user_following = User.objects.create(username='Автор')
        self.user_follower = User.objects.create(username='Подписчик')
        self.post = Post.objects.create(
            author=self.user_following,
            text='Какой-то пост'
        )
        self.client_following.force_login(self.user_following)
        self.client_follower.force_login(self.user_follower)

    def test_authorized_user_can_follow(self):
        """
        Авторизованный пользователь может
        подписываться на других пользователей.
        """
        self.client_follower.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_following.username})
        )
        new_follow = Follow.objects.all().count()
        self.assertEqual(new_follow, 1)
        self.assertTrue(Follow.objects.filter(
            user=self.user_follower,
            author=self.user_following
        ).exists())

    def test_authorized_user_can_unfollow(self):
        """
        Авторизованный пользователь может
        отписываться от других пользователей.
        """
        self.client_follower.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_following.username})
        )
        self.client_follower.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_following.username})
        )
        new_follow = Follow.objects.all().count()
        self.assertEqual(new_follow, 0)
        self.assertFalse(Follow.objects.filter(
            user=self.user_follower,
            author=self.user_following
        ).exists())

    def test_new_post_for_follower(self):
        """
        Новая запись пользователя появляется
        в ленте тех, кто на него подписан.
        """
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        follower_response = self.client_follower.get(
            reverse('posts:follow_index'))
        self.assertTrue(Follow.objects.filter(
            user=self.user_follower,
            author=self.user_following
        ).exists())
        new_posts_follower = follower_response.context['page_obj']
        self.assertIn(self.post, new_posts_follower)

    def test_new_post_is_not_for_unfollower(self):
        """
        Новая запись пользователя не появляется
        в ленте тех, кто на него не подписан.
        """
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        self.client_follower.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_following.username})
        )
        self.assertFalse(Follow.objects.filter(
            user=self.user_follower,
            author=self.user_following
        ).exists())
        unfollower_responce = self.client_follower.get(
            reverse('posts:follow_index'))
        new_posts_unfollower = unfollower_responce.context['page_obj']
        self.assertEqual((len(new_posts_unfollower)), 0)
