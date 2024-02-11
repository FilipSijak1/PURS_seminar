SELECT * FROM korisnik WHERE
password = UNHEX(SHA2('{{passwd}}', 256))
AND korisnicko_ime = '{{user}}';