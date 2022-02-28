from django.db import models


# Create your models here.
# 都道府県
class Prefecture(models.Model):
    name = models.CharField("都道府県名", max_length=10)

    def __str__(self):
        return f"{self.id},{self.name}"


# 市区町村
class City(models.Model):
    prefecture = models.ForeignKey(Prefecture, on_delete=models.CASCADE, related_name='city')
    name = models.CharField("市区町村名", max_length=10)

    def __str__(self):
        return f"{self.id},{self.name}"


# 依頼機関
class Client(models.Model):
    prefecture = models.ForeignKey(Prefecture, on_delete=models.CASCADE, related_name='client', null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='client', null=True, blank=True)
    department = models.CharField("部局", max_length=100)

    def __str__(self):
        return f"{self.id},{self.prefecture.name},{self.department}"


# 入札案件
class Project(models.Model):
    name = models.CharField("案件名", max_length=100)
    serial_no = models.CharField("案件番号", max_length=100, null=True, blank=True)
    BID_METHOD_CHOICES = (
        (0, '電子調達'),
        (1, '紙調達')
    )
    bid_method_type = models.IntegerField("入札方法", choices=BID_METHOD_CHOICES, default=0)
    BID_FORMAT_CHOICES = (
        (0, '一般競争入札'),
        (1, '指名競争入札'),
        (2, '企画競争'),
        (3, '随意契約'),
    )
    bid_format_type = models.IntegerField("入札形式", choices=BID_FORMAT_CHOICES)
    CATEGORY_CHOICES = (
        (0, '工事'),
        (1, 'コンサル'),
        (2, '物品'),
        (3, '委託'),
        (4, 'その他'),
    )
    category_type = models.IntegerField("調達区分", choices=CATEGORY_CHOICES)
    sector = models.CharField("業種品目", max_length=100, null=True, blank=True)
    place = models.CharField("業務場所", max_length=100, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='project')
    description = models.CharField("案件概要", max_length=10000, null=True, blank=True)
    etc = models.CharField("案件備考", max_length=10000, null=True, blank=True)
    release_date = models.DateTimeField("公示日", null=True, blank=True)
    orientation_date = models.DateTimeField("説明会日程", null=True, blank=True)
    entry_from = models.DateTimeField("参加申請開始", null=True, blank=True)
    entry_to = models.DateTimeField("参加申請終了", null=True, blank=True)
    submit_from = models.DateTimeField("資料等提出開始", null=True, blank=True)
    submit_to = models.DateTimeField("資料等提出終了", null=True, blank=True)
    opening_date = models.DateTimeField("開札日")
    estimated_price = models.IntegerField("予定金額", null=True, blank=True)
    crawl_url = models.URLField("クロール先URL", null=True, blank=True)

    contract_date = models.DateTimeField("契約日", null=True, blank=True)
    contract_price = models.IntegerField("契約金額", null=True, blank=True)
    contract_from = models.DateTimeField("履行期間開始", null=True, blank=True)
    contract_to = models.DateTimeField("履行期間終了", null=True, blank=True)

    created_on = models.DateTimeField("登録日時", auto_now_add=True)
    updated_on = models.DateTimeField("修正日時", auto_now=True)
    deleted_at = models.DateTimeField("削除日時", blank=True, null=True)

    def __str__(self):
        return f"{self.id},{self.name}"

    # def get_client_prefecture_name(self):
    #     return self.client.prefecture.name


# 添付ファイル
class AttachedFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='attach_file')
    name = models.CharField("添付ファイル名", max_length=100)
    path = models.CharField("添付ファイルパス", max_length=255)


# 入札業者
class Bidder(models.Model):
    name = models.CharField("入札業者名", max_length=100)
    serial_no = models.CharField("法人番号", max_length=50, null=True, blank=True)
    prefecture = models.ForeignKey(Prefecture, on_delete=models.CASCADE, related_name='bidder', null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='bidder', null=True, blank=True)
    representative = models.CharField("代表者名", max_length=32, null=True, blank=True)
    mail = models.CharField("メールアドレス", max_length=255, null=True, blank=True)
    password = models.CharField("パスワード", max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.id},{self.name}"


# 入札結果
class BidResult(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bid_result')
    bidder = models.ForeignKey(Bidder, on_delete=models.CASCADE, related_name='bid_result')
    price = models.IntegerField("契約金額", blank=True, null=True)
    bid_count = models.IntegerField("入札回数", default=1)
    RESULT_CHOICES = (
        (0, '落札失敗'),
        (1, '落札'),
        (2, '辞退'),
    )
    result_type = models.IntegerField("結果", choices=RESULT_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.id},{self.project.name},{self.bidder.name}"


