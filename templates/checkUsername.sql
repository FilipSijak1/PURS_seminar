-- templates/checkUsername.sql
SELECT * FROM korisnik WHERE korisnicko_ime = :korisnicko_ime;
