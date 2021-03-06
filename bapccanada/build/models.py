from django.db import models
from django.template.defaultfilters import slugify
from django.utils import timezone

from functools import reduce
from decimal import Decimal


from bapccanada.utils import create_shortcode
from products.models import GPU, CPU, RAM, Monitor, Motherboard, PowerSupply, Case, Storage, Cooler, Image
from user.models import UserProfile


class Build(models.Model):
    gpu = models.ForeignKey(GPU, null=True, on_delete=models.DO_NOTHING)
    cpu = models.ForeignKey(CPU, null=True, on_delete=models.DO_NOTHING)
    ram = models.ForeignKey(RAM, null=True, on_delete=models.DO_NOTHING)
    monitor = models.ForeignKey(Monitor, null=True, on_delete=models.DO_NOTHING)
    motherboard = models.ForeignKey(Motherboard, null=True, on_delete=models.DO_NOTHING)
    power_supply = models.ForeignKey(PowerSupply, null=True, on_delete=models.DO_NOTHING)
    storage = models.ForeignKey(Storage, null=True, on_delete=models.DO_NOTHING)
    case = models.ForeignKey(Case, null=True, on_delete=models.DO_NOTHING)
    cooler = models.ForeignKey(Cooler, null=True, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=100, null=True)
    owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True)
    complete = models.BooleanField(default=False)
    slug = models.SlugField(blank=True)
    anonymous_session = models.CharField(max_length=200, null=True, unique=True)
    total_price = models.DecimalField(default=0.0, max_digits=19, decimal_places=2, blank=True, null=True)
    points = models.IntegerField(default=0, blank=True, null=True)
    date_published = models.DateTimeField(default=timezone.now, editable=True)
    date_created = models.DateTimeField(auto_now_add=True)
    shortcode = models.CharField(max_length=6, blank=True, unique=True, null=True, default=None)
    flag_pristine = models.BooleanField(default=True, editable=False)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        self.total_price = self.get_total_price()
        if (self.shortcode is None or self.shortcode == "") and not self.is_pristine():
            self.shortcode = create_shortcode(instance=Build)
        super(Build, self).save(*args, **kwargs)

    def __str__(self):
        return "{} - {}".format(self.owner, self.name)

    @staticmethod
    def track_current_build(current_user):
        current_build = CurrentBuild.objects.filter(tracked_user=current_user).first()

        if current_build is None:
            new_build = Build.objects.create(owner=current_user)
            current_build = CurrentBuild.objects.create(tracked_user=current_user, tracked_build=new_build)

        return current_build.tracked_build

    @staticmethod
    def handle_build_tracking(request):
        if request.user.is_authenticated:
            build_to_return = Build.track_current_build(request.user.userprofile)
        else:
            if not request.session.session_key:
                request.session.create()

            build_to_return = Build.objects.get_or_create(anonymous_session=request.session.session_key)[0]

        return build_to_return

    @staticmethod
    def transfer_anonymous_build(request, authenticated_user):
        session_key = request.session.session_key

        if session_key is not None:
            anonymous_build = Build.objects.filter(anonymous_session=session_key).first()

            if anonymous_build is not None:
                # if this user made an anonymous build, transfer it over
                anonymous_build.anonymous_session = None
                anonymous_build.owner = authenticated_user.userprofile
                anonymous_build.save()

                # update authenticated_user's current build so they see it upon clicking build
                current_build = CurrentBuild.objects.get_or_create(tracked_user=authenticated_user.userprofile)[0]
                current_build.tracked_build = anonymous_build
                current_build.save()

    def get_component_array(self):
        return [self.gpu, self.cpu, self.monitor, self.ram, self.cooler, self.motherboard, self.power_supply, self.case,
                self.storage]

    def get_total_price(self):
        component_array = self.get_component_array()
        component_array = map(lambda component: Decimal(0.0) if not component else (Decimal(component.cheapest_price)
                                                                                    + Decimal(
                    component.cheapest_price_shipping))
                              , component_array)

        return reduce(lambda total, current: total + current, component_array)

    def modify_component(self, component, modifier):
        replacement_value = None if modifier == "remove" else component
        component_type = component.get_real_instance_class()

        if component_type == CPU:
            self.cpu = replacement_value
        elif component_type == GPU:
            self.gpu = replacement_value
        elif component_type == RAM:
            self.ram = replacement_value
        elif component_type == Motherboard:
            self.motherboard = replacement_value
        elif component_type == PowerSupply:
            self.power_supply = replacement_value
        elif component_type == Case:
            self.case = replacement_value
        elif component_type == Storage:
            self.storage = replacement_value
        elif component_type == Cooler:
            self.cooler = replacement_value
        else:
            self.monitor = replacement_value

        self.save()

    def is_pristine(self):
        component_dict = self.get_component_dict()
        for key, component in component_dict.items():
            if component['object'] is not None:
                self.flag_pristine = False
                break
        return self.flag_pristine

    def clean_build(self):
        self.cpu = None
        self.gpu = None
        self.monitor = None
        self.case = None
        self.cooler = None
        self.motherboard = None
        self.power_supply = None
        self.ram = None
        self.storage = None
        self.save()

    def get_component_dict(self):
        return {
            "Video Card": {
                "object": self.gpu,
                "category_link": "products:gpu",
                "detail_link": "products:gpu_detail",
                "thumbnail": self.gpu.get_thumbnail() if self.gpu else ""
            },
            "Processor": {
                "object": self.cpu,
                "category_link": "products:cpu",
                "detail_link": "products:cpu_detail",
                "thumbnail": self.cpu.get_thumbnail() if self.cpu else ""
            },
            "Monitor": {
                "object": self.monitor,
                "category_link": "products:monitors",
                "detail_link": "products:monitor_detail",
                "thumbnail": self.monitor.get_thumbnail() if self.monitor else ""
            },
            "Memory": {
                "object": self.ram,
                "category_link": "products:ram",
                "detail_link": "products:ram_detail",
                "thumbnail": self.ram.get_thumbnail() if self.ram else ""
            },
            "Motherboard": {
                "object": self.motherboard,
                "category_link": "products:motherboard",
                "detail_link": "products:motherboard_detail",
                "thumbnail": self.motherboard.get_thumbnail() if self.motherboard else ""
            },
            "Power Supply": {
                "object": self.power_supply,
                "category_link": "products:power_supply",
                "detail_link": "products:power_supply_detail",
                "thumbnail": self.power_supply.get_thumbnail() if self.power_supply else ""
            },
            "Storage": {
                "object": self.storage,
                "category_link": "products:storage",
                "detail_link": "products:storage_detail",
                "thumbnail": self.storage.get_thumbnail() if self.storage else ""
            },
            "Case": {
                "object": self.case,
                "category_link": "products:case",
                "detail_link": "products:case_detail",
                "thumbnail": self.case.get_thumbnail() if self.case else ""
            },
            "CPU Cooler": {
                "object": self.cooler,
                "category_link": "products:cooler",
                "detail_link": "products:cooler_detail",
                "thumbnail": self.cooler.get_thumbnail() if self.cooler else ""
            }
        }

    def get_build_status(self):
        if not self.complete:
            return "Incomplete"
        else:
            return "Complete"

    def get_link(self):
        return "/list/" + self.shortcode


class CurrentBuild(models.Model):
    tracked_user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True)
    tracked_build = models.OneToOneField(Build, on_delete=models.SET_NULL, null=True)
