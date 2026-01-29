from app import db
from app.models import Tutor, User, Booking, Review

import math
from collections import Counter


def tf(text):
    words = text.lower().split()
    return Counter(words)


def idf(docs):
    N = len(docs)
    idf_values = {}
    for doc in docs:
        for word in set(doc):
            idf_values[word] = idf_values.get(word, 0) + 1
    return {w: math.log(N / c) for w, c in idf_values.items()}


def tfidf(text, idf_values):
    tf_values = tf(text)
    return {w: tf_values[w] * idf_values.get(w, 0) for w in tf_values}


def cosine_similarity(vec1, vec2):
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[x] * vec2[x] for x in intersection)

    sum1 = sum(v**2 for v in vec1.values())
    sum2 = sum(v**2 for v in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    return numerator / denominator


class RecommendationEngine:
    def recommend_tutors_for_student(self, student_id, limit=5):
        student = User.query.get(student_id)

        student_bookings = Booking.query.filter_by(student_id=student_id).all()

        preferred_subjects = set()
        for booking in student_bookings:
            if booking.subject:
                preferred_subjects.update(
                    [s.strip().lower() for s in booking.subject.split(",")]
                )

        all_tutors = Tutor.query.filter_by(is_verified=True, is_available=True).all()

        if not preferred_subjects:
            return sorted(all_tutors, key=lambda x: x.rating, reverse=True)[:limit]

        tutor_profiles = []
        tutor_objects = []

        for tutor in all_tutors:
            profile_text = f"{tutor.subjects} {tutor.level} {tutor.bio}".lower()
            tutor_profiles.append(profile_text.split())
            tutor_objects.append(tutor)

        student_profile = " ".join(preferred_subjects).lower().split()

        documents = [student_profile] + tutor_profiles
        idf_values = idf(documents)

        student_vec = tfidf(" ".join(student_profile), idf_values)

        tutor_scores = []
        for tutor, profile in zip(tutor_objects, tutor_profiles):
            tutor_vec = tfidf(" ".join(profile), idf_values)
            score = cosine_similarity(student_vec, tutor_vec)

            # ⭐ rating boost
            rating_boost = tutor.rating / 5.0 * 0.3
            score *= 1 + rating_boost

            # 📍 location boost
            if student.location and tutor.user.location == student.location:
                score *= 1.2

            tutor_scores.append((tutor, score))

        tutor_scores.sort(key=lambda x: x[1], reverse=True)
        return [tutor for tutor, _ in tutor_scores[:limit]]
