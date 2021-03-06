import re

from django import forms
from products.models import Review
from user.models import UserProfile, ClickSettings, EmailSettings, PrivacySettings


class AvatarUrlForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar_url']

    def clean_avatar_url(self):
        ext = ["jpeg", "jpg", "gif", "png"]
        url = self.cleaned_data.get('avatar_url')
        if url.endswith(tuple(ext)) is False:
            raise forms.ValidationError("Not a valid image link")
        return url


class BiographyForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['biography']


class ClickSettingsForm(forms.ModelForm):
    class Meta:
        model = ClickSettings
        fields = ['links_as_new_window']
        labels = {
            'links_as_new_window': 'open links as a new window'
        }


class EmailSettingsForm(forms.ModelForm):
    class Meta:
        model = EmailSettings
        fields = ['messeges_as_emails', 'send_email_digest', 'unsubscribe_from_all_emails']


class PrivacySettingsForm(forms.ModelForm):
    class Meta:
        model = PrivacySettings
        fields = ['data_for_research', 'index_profile']
        labels = {
            'data_for_research': "allow my data to be used for research purposes",
            'index_profile': "don't allow search engines to index my user profile"
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['content']
