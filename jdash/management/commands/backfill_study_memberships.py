from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from jdash.config import constants
from jdash.models import Study, StudyMembership


class Command(BaseCommand):
    help = "Populate study memberships from study owners and legacy study groups."

    def add_arguments(self, parser):
        parser.add_argument(
            "--study",
            dest="study_title",
            help="Backfill only the study with this exact title.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change and roll back all database writes.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        studies = Study.objects.all().order_by("title")
        study_title = options.get("study_title")
        if study_title:
            studies = studies.filter(title=study_title)
            if not studies.exists():
                raise CommandError(f'No study exists with title "{study_title}".')

        created = 0
        updated = 0
        unchanged = 0
        studies_without_owner = 0

        for study in studies.iterator():
            if study.owner_id:
                _membership, was_created = StudyMembership.objects.update_or_create(
                    study_id=study.pk,
                    user_id=study.owner_id,
                    defaults={
                        "role": StudyMembership.Role.MAINTAINER,
                        "added_by_id": study.owner_id,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            else:
                studies_without_owner += 1
                self.stdout.write(
                    self.style.WARNING(f"Skipped owner membership for {study.title}: no owner assigned.")
                )

            try:
                study_group = Group.objects.get(name=f"{study.title}_group")
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"No legacy study group found for {study.title}.")
                )
                continue

            members = study_group.user_set.prefetch_related("groups").all()
            for user in members.iterator(chunk_size=500):
                if user.pk == study.owner_id:
                    role = StudyMembership.Role.MAINTAINER
                else:
                    group_names = set(user.groups.values_list("name", flat=True))
                    if constants.group_name_administrator in group_names:
                        role = StudyMembership.Role.MAINTAINER
                    elif constants.group_name_investigator in group_names:
                        role = StudyMembership.Role.INVESTIGATOR
                    else:
                        role = StudyMembership.Role.VIEWER

                membership, was_created = StudyMembership.objects.get_or_create(
                    study_id=study.pk,
                    user_id=user.pk,
                    defaults={
                        "role": role,
                        "added_by_id": study.owner_id,
                    },
                )
                if was_created:
                    created += 1
                    self.stdout.write(
                        f"Added {user.username} to {study.title} as {membership.get_role_display()}."
                    )
                else:
                    unchanged += 1

        if options["dry_run"]:
            transaction.set_rollback(True)
            prefix = "Dry run complete"
        else:
            prefix = "Backfill complete"

        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}: {created} created, {updated} owner memberships refreshed, "
                f"{unchanged} already present, {studies_without_owner} studies without an owner."
            )
        )
