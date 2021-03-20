# from consents.models import Consent, Term, TermOption
# from workshops.models import Person
# from rest_framework import serializers

# class ConsentSerializer(serializers.Serializer):
#     term =
#     answer
#     date_consented


#     @classmethod
#     def from_all_active_terms(person: Person):
#         terms = Term.objects.active()
#         consents = Consent.objects.active()
#         consent_by_term_id = {
#             consent.term_id: consent
#             for consent in consents
#         }
#         for term in terms:
#             ConsentSerializer(
#                term=term,
#                consent=consent_by_term_id.get(term.id)
#             )

# class TermSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Term
#         fields = ['slug', 'content', 'required_type']

# class TermOptionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TermOption
#         fields = ['option_type', 'content']


# class ConsentSerializer(serializers.ModelSerializer):
#     term = TermSerializer
#     term_option = TermOptionSerializer
#     class Meta:
#         model = Consent
#         fields = ['person', 'created_at']


#     @classmethod
#     def from_all_active_terms(person: Person):
#         terms = Term.objects.active()
#         consents = Consent.objects.active()
#         consent_by_term_id = {
#             consent.term_id: consent
#             for consent in consents
#         }
#         for term in terms:
#             ConsentSerializer(
#                term=TermSerializer(term),
#                term_option=TermOptionSerializer(
#                consent=consent_by_term_id.get(term.id)
#             )
