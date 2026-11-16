# Revokes old "Apple Development" certificates before an iPhone build.
# Each cloud build gets a fresh Mac with no keychain, so Xcode creates a new
# development certificate every time, and Apple caps how many an account can have.
# These certificates are only used by the build itself; distribution certificates
# (what the App Store build is signed with) are never touched.
#
# Usage: ruby revoke_dev_certs.rb KEY_ID ISSUER_ID PATH_TO_P8
require 'openssl'
require 'json'
require 'net/http'
require 'base64'

key_id, issuer, p8 = ARGV
abort 'usage: revoke_dev_certs.rb KEY_ID ISSUER_ID P8' unless key_id && issuer && p8

b64 = ->(s) { Base64.urlsafe_encode64(s, padding: false) }
now = Time.now.to_i
data = b64.(JSON.generate(alg: 'ES256', kid: key_id, typ: 'JWT')) + '.' +
       b64.(JSON.generate(iss: issuer, iat: now, exp: now + 600, aud: 'appstoreconnect-v1'))
key = OpenSSL::PKey.read(File.read(p8))
der = key.sign(OpenSSL::Digest::SHA256.new, data)
r, s = OpenSSL::ASN1.decode(der).value.map { |v| v.value.to_s(2).rjust(32, "\0")[-32, 32] }
token = data + '.' + b64.(r + s)

http = Net::HTTP.new('api.appstoreconnect.apple.com', 443)
http.use_ssl = true
auth = { 'Authorization' => "Bearer #{token}" }

res = http.get('/v1/certificates?limit=200&fields[certificates]=certificateType,name,expirationDate', auth)
abort "list failed: #{res.code} #{res.body[0, 300]}" unless res.code == '200'
certs = JSON.parse(res.body)['data']
dev = certs.select { |c| %w[DEVELOPMENT IOS_DEVELOPMENT].include?(c['attributes']['certificateType']) }
puts "#{certs.size} certificates, #{dev.size} development"
dev.each do |c|
  d = http.delete("/v1/certificates/#{c['id']}", auth)
  puts "revoke #{c['attributes']['name']} (#{c['attributes']['certificateType']}): #{d.code}"
end
