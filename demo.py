from urielplus import urielplus

u = urielplus.URIELPlus()

u.reset()

#Configuration
u.set_cache(True)

#Aggregation
# u.set_aggregation('A')

#Integrating databases
u.integrate_databases()

#Feature Coverage
# u.all_feature_coverage()

# Imputation
u.softimpute_imputation()

#Feature Coverage
# u.all_feature_coverage()

#Distance Calculation
print(u.new_distance("scriptural", "stan1290", "stan1293"))