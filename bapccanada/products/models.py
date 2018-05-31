from django.db import models
from django.db.models import Min, Avg
from django.db.models.signals import m2m_changed
from django.template.defaultfilters import slugify

from polymorphic.models import PolymorphicModel

from home.models import Price, Image
from user.models import UserProfile


class Component(PolymorphicModel):
    manufacturer = models.CharField(max_length=30)
    model_number = models.CharField(max_length=30, blank=True)
    serial_number = models.CharField(max_length=30, blank=True)
    display_name = models.CharField(max_length=100, default="")
    display_title = models.CharField(max_length=200, default="")

    last_updated = models.DateTimeField(auto_now=True)
    slug = models.SlugField(blank=True)

    images = models.ManyToManyField(Image)
    prices = models.ManyToManyField(Price)
    cheapest_price = models.DecimalField(default=0.0, max_digits=19, decimal_places=2, blank=True, null=True)

    average_rating = models.DecimalField(default=0.0, max_digits=2, decimal_places=1, blank=True, null=True)
    num_ratings = models.PositiveIntegerField(default=0)

    def __str__(self):
        return "{} - {}".format(self.manufacturer, self.model_number)

    def save(self, *args, **kwargs):
        if self.model_number != "":
            self.display_name = "{} {}".format(self.manufacturer, self.model_number)
            self.slug = slugify(self.model_number)
        else:
            self.display_name = "{} {}".format(self.manufacturer, self.serial_number)
            self.slug = slugify(self.serial_number)

        self.slug += "-" + slugify(self.id)
        self.display_title = self.get_page_title()

        super(Component, self).save(*args, **kwargs)

    def update_ratings(self):
        num_ratings = Review.objects.filter(component=self)
        self.num_ratings = num_ratings.count()
        self.average_rating = num_ratings.aggregate(Avg("stars"))["stars__avg"]
        self.save()

    # used for component detail title
    def get_page_title(self):
        pass

    def get_component_images(self):
        return self.images.all()

    def get_component_prices(self):
        return self.prices.all()

    def get_component_reviews(self):
        return Review.objects.filter(component=self)[:5]

    def get_tech_details(self):
        return {
            "Manufacturer": self.manufacturer,
            "Model": self.model_number,
            "Part #": self.serial_number
        }


class GPU(Component):
    clock_rate = models.DecimalField(default=0.0, max_digits=3, decimal_places=2, blank=True, null=True)
    chipset = models.CharField(max_length=100)
    clock_rate_oc = models.DecimalField(default=0.0, max_digits=3, decimal_places=2, blank=True, null=True)
    memory_size = models.PositiveIntegerField(default=10)
    hdmi_ports = models.PositiveIntegerField(default=0)
    dp_ports = models.PositiveIntegerField(default=0)

    def get_page_title(self):
        return "{} - {} {}GB {} Video Card".format(self.manufacturer, self.chipset,
                                                   self.memory_size, self.model_number)

    def get_tech_details(self):
        main_details = super(GPU, self).get_tech_details()
        extra_details = {
            "Chipset": self.chipset,
            "Memory Size": "{}GB".format(self.memory_size),
            "Base Clock": "{}Ghz".format(self.clock_rate),
            "Boost Clock": "{}Ghz".format(self.clock_rate_oc),
            "Displayport": self.dp_ports,
            "HDMI": self.hdmi_ports
        }

        return {**main_details, **extra_details}


class CPU(Component):
    cores = models.PositiveIntegerField(default=2)
    threads = models.PositiveIntegerField(default=4)
    socket = models.CharField(max_length=100)
    integrated_graphics = models.CharField(max_length=100, null=True)
    stock_freq = models.DecimalField(default=0.0, max_digits=2, decimal_places=1, blank=True, null=True)
    boost_freq = models.DecimalField(default=0.0, max_digits=2, decimal_places=1, blank=True, null=True)
    watts = models.PositiveIntegerField(default=0)
    l3_cache = models.CharField(max_length=20)

    def get_page_title(self):
        return "{} - {} {}Ghz {}-Core Processor".format(self.manufacturer, self.model_number,
                                                        self.stock_freq, self.cores)

    def get_tech_details(self):
        main_details = super(CPU, self).get_tech_details()
        extra_details = {
            "Stock Frequency": "{}Ghz".format(self.stock_freq),
            "Turbo Frequency": "{}Ghz".format(self.boost_freq),
            "Cores": self.cores,
            "Threads": self.threads,
            "L3 Cache": self.l3_cache,
            "Power Draw": "{} Watts".format(self.watts),
            "Integrated Graphics": self.integrated_graphics
        }

        return {**main_details, **extra_details}


class Monitor(Component):
    screen_size = models.PositiveIntegerField(default=10)
    resolution = models.CharField(max_length=100)
    aspect_ratio = models.CharField(max_length=100)
    response_time = models.PositiveIntegerField(default=10)
    refresh_rate = models.PositiveIntegerField(default=60)
    g_sync = models.CharField(max_length=100)
    dp_ports = models.IntegerField(default=0)
    hdmi_ports = models.IntegerField(default=0)
    panel_type = models.CharField(max_length=20)

    def get_page_title(self):
        resolution = "{}".format(self.resolution).replace(' ', "")
        return "{} - {} {}\" {} {}Hz Monitor".format(self.manufacturer, self.serial_number, self.screen_size,
                                                     resolution, self.refresh_rate)

    def get_tech_details(self):
        main_details = super(Monitor, self).get_tech_details()
        extra_details = {
            "Screen Size": "{}\"".format(self.screen_size),
            "Resolution": self.resolution,
            "Aspect Ratio": self.aspect_ratio,
            "Response Time": "{}ms".format(self.response_time),
            "Refresh Rate": "{}Hz".format(self.refresh_rate),
            "G-Sync": self.g_sync,
            "Panel Type": self.panel_type,
            "Displayport": self.dp_ports,
            "HDMI": self.hdmi_ports
        }

        return {**main_details, **extra_details}


def prices_changed(sender, **kwargs):
    if kwargs["action"] == "post_add" and kwargs["model"] == Price:
        current_component = kwargs["instance"]
        current_min_price = current_component.prices.all().aggregate(Min('price'))["price__min"]
        if current_component.cheapest_price == 0.0 or current_min_price < current_component.cheapest_price:
            current_component.cheapest_price = current_min_price
            current_component.save()


# many to many handler to update lowest price
m2m_changed.connect(prices_changed, sender=Component.prices.through)


class Review(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    component = models.ForeignKey(Component, on_delete=models.CASCADE, null=True)
    content = models.CharField(max_length=1000)
    stars = models.DecimalField(default=0.0, max_digits=2, decimal_places=1, blank=True, null=True)
    time_added = models.DateTimeField(auto_now=True)
    time_edited = models.DateTimeField(auto_now=True)
    points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return "{} - {}".format(self.user, self.id)

    def save(self, *args, **kwargs):
        # must save first or we cannot find ourselves when updating component stats
        super(Review, self).save(*args, **kwargs)
        if self.component:
            self.component.update_ratings()
