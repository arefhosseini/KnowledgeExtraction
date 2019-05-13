from django.db import models


class Relation(models.Model):
    subject = models.CharField(max_length=200, null=False)
    predicate = models.CharField(max_length=200, null=False)
    object = models.CharField(max_length=200, null=False)

    def __str__(self):
        return "%s %s %s" % (self.subject, self.predicate, self.object)


class Text(models.Model):
    text = models.TextField(null=False, blank=False)

    def __str__(self):
        return "%s" % self.text

