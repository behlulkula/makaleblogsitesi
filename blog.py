from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

#Kullanıcı Giriş decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapınız.", "danger")
            return redirect(url_for("login"))
    return decorated_function

#Kullanıcı kayıt formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim:", validators=[validators.DataRequired(message="Lütfen isminiz ve soyisminizi giriniz")])
    username = StringField("Kullanıcı Adı:", validators=[validators.Length(message="4-25 karakter arası giriniz",min = 4, max = 25), validators.DataRequired(message="Lütfen bir kullanıcı adı belirleyiniz")])
    email = StringField("Mail Adresi:", validators=[validators.DataRequired(), validators.Email(message="Lütfen geçerli bir email adresi girin")])
    password = PasswordField("Parola:", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyiniz"),
        validators.EqualTo(fieldname="confirm", message="Parolanız uyuşmuyor")
        ])
    confirm = PasswordField("Parola Tekrar:", validators=[validators.DataRequired(message="Lütfen parolanızı tekrar girin")])

#Kullanıcı giriş formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

app = Flask(__name__)
app.secret_key= "behlulblog" #flash mesaj çıkarmak için gerekli

#flask ile mysql ilişkisini kurma
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "behlulblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)


#Anasayfanın URL'si
@app.route("/")
def index():
    return render_template("index.html")

#Hakkımda sayfasının URL'si
@app.route("/about")
def about():
    return render_template("about.html")

#Makaleler sayfasının URL'si
@app.route("/article")
def article():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("article.html", articles = articles) 
    else:
        return render_template("article.html")

#Kontrol paneli sayfasının URL'si
@app.route("/dashboard")
@login_required #giriş yapmayan bu sayfaya ulaşamaz
def dashboard():
    #buradan önce kullanıcının ismini çekiyoruz kullanıcı_adı'nı kullanarak
    cursor = mysql.connection.cursor()
    sorgu_name = "SELECT * FROM users WHERE username = %s"
    result_name = cursor.execute(sorgu_name,(session["username"],))
    sorgu_data = cursor.fetchone()
    author_name = sorgu_data["name"]
    #sonra bu adı sorgulayarak data çekeceğiz
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(sorgu,(author_name,))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

#Kayıt sayfasının URL'si
@app.route("/register", methods = ["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():

        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = form.password.data #sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()

        cursor.close()

        flash("Başarıyla kayıt oldunuz.","success")

        return redirect(url_for("login")) #login() fonksiyonunu çalıştırıyor

    else: 
        return render_template("register.html", form = form)

#Giriş yap sayfasının URL'si
@app.route("/login", methods =["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()

        sorgu = "SELECT * FROM users WHERE username = %s"

        result = cursor.execute(sorgu,(username,)) #eğer username yoksa 0 geliyor sonuç

        if result > 0:
            data = cursor.fetchone() #çekilen veriyi sözlük haline çeviriyoruz
            real_password = data["password"] 
            if real_password == password_entered: # if sha256_crypt.verify(password_entered,real_password)
                cursor.close()
                flash("Başarıyla Giriş Yaptınız", "success")
                
                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                cursor.close()
                flash("Parolayı Yanlış Girdiniz.", "danger")
                return redirect(url_for("login"))

        else:
            cursor.close()
            flash("Böyle bir kullanıcı adı bulunmuyor.","danger")
            return redirect(url_for("login"))

    else:
        return render_template("login.html", form = form)


#Makale detayları sayfasının URL'si

@app.route("/articles/<string:id>")
def articles(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("articles.html", article = article)
    else:
        return render_template("articles.html")

#Çıkış yap sayfasının URL'si
@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla Çıkış Yaptınız.","success")
    return redirect(url_for("index"))

#Makale ekle sayfasının URL'si
@app.route("/addarticle", methods = ["GET", "POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu_name = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(sorgu_name,(session["username"],))
        sorgu_data = cursor.fetchone()
        author_name = sorgu_data["name"]
        sorgu = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,author_name,content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla eklendi.","success")
        return redirect(url_for("article"))

    else:
        return render_template("addarticle.html", form = form)

#Makale silme sayfasının URL'si
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu_name = "SELECT * FROM users WHERE username = %s"
    result_name = cursor.execute(sorgu_name,(session["username"],))
    sorgu_data = cursor.fetchone()
    author_name = sorgu_data["name"]
    
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s AND id = %s"
    result = cursor.execute(sorgu,(author_name,id))

    if result > 0:
        sorgu2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()

        flash("Makale başarıyla silindi.","success")
        return redirect(url_for("dashboard"))

    else:
        flash("Böyle bir makale bulunmuyor veya bu işlem için yetkiniz yok","danger")
        return redirect(url_for("index"))

#Makale güncelleme sayfasının URL'si
@app.route("/edit/<string:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    cursor = mysql.connection.cursor()
    sorgu_name = "SELECT * FROM users WHERE username = %s"
    result_name = cursor.execute(sorgu_name,(session["username"],))
    sorgu_data = cursor.fetchone()
    author_name = sorgu_data["name"]

    if request.method == "GET":
        cursor =mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE id = %s AND author = %s"
        result = cursor.execute(sorgu,(id,author_name))

        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form)
        
    else:
        #post request kısmı
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))

        mysql.connection.commit()

        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("dashboard"))

#Makale formu
class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.DataRequired(message="Lütfen bir başlık giriniz")])
    content = TextAreaField("Makale İçeriği", validators=[validators.DataRequired(message="Lütfen bir içerik giriniz")])

#Arama sayfasının URL'si
@app.route("/search", methods=["GET","POST"])
def search():
    if request.method == "GET": #direk sayfanın açılmasını engellemek için, sadece post olursa açılacak
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword") #forma yazdığımız name="keyword"ü alıyoruz böylelikle
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%'" #'%beh%' aradaki beh'i değişkene atadık
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı.","warning")
            return redirect(url_for("article"))
        else:
            articles = cursor.fetchall()
            return render_template("article.html", articles = articles)


if __name__ == "__main__":
    app.run(debug=True)